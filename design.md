# Design — Internet's Dream

## Architecture

```
                 ┌──────────────────────────────────────────┐
                 │            Sources (read-only)           │
                 │  WhatsApp _chat.txt · DiscordChatExporter │
                 │  JSON · Gmail/Cal/Photos (planned)        │
                 └──────────────────┬───────────────────────┘
                                    │ ingest
                 ┌──────────────────▼───────────────────────┐
                 │            dreamcore (Python)            │
                 │  parsers → chunker → embedder → store    │
                 │  store: SQLite + AES-256-GCM payloads    │
                 │  index: FTS5 (plaintext metadata)        │
                 │  LLM gateway: OpenAI-compat / Anthropic  │
                 └───────┬───────────────┬──────────┬───────┘
                         │ REST/JSON     │          │ file state
              ┌──────────▼───┐   ┌───────▼────┐  ┌──▼───────────┐
              │ web-dashboard│   │ desktop-   │  │ agents/      │
              │ (Material 3, │   │ linux      │  │ orchestrator │
              │  GitHub Pages│   │ (PyQt6)    │  │ (goal/design/│
              │  + demo mode)│   │            │  │  handoff.md) │
              └──────────────┘   └────────────┘  └──────────────┘
              ┌──────────────┐   ┌────────────┐
              │ desktop-mac  │   │ mobile-    │
              │ SwiftUI      │   │ android    │
              │ Liquid Glass │   │ Compose M3 │
              └──────────────┘   └────────────┘
```

## Key decisions

- **Encryption**: every document payload is AES-256-GCM encrypted with a key
  derived (PBKDF2-HMAC-SHA256, 600k iterations) from a user passphrase stored
  in `~/.internet-dream/key`. The FTS5 index holds only plaintext
  source/timestamp/sender metadata needed for search — documented honestly.
- **Embeddings**: default local hashing embedder (deterministic, offline,
  zero deps). Optional OpenAI-compatible `/v1/embeddings` endpoint via config.
- **Search**: hybrid — FTS5 keyword match + cosine similarity over stored
  vectors; RRF merge. `/ask` does retrieve-then-generate through the gateway.
- **Web on Pages**: GitHub Pages is static-only, so the dashboard ships a
  seeded demo dataset in `demo-data.js` and works fully offline; when the
  `dreamcore` API is reachable (configurable endpoint) it switches to live
  mode. No secrets are ever shipped.
- **Native shells are thin clients**: they talk to the local `dreamcore serve`
  API; nothing sensitive leaves the machine except LLM calls the user
  explicitly configures.
- **No license**: no LICENSE file; UNLICENSE-style statement only in README.

## State protocol

`goal.md` (success criteria), `design.md` (this file), `handoff.md`
(phase log + next actions) are the agent memory. Updated after every phase.
