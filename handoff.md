# Handoff — Internet's Dream

## Phase log

### Phase 1 — Initialization & Scaffold (done)
- Repo scaffolded: core/, web-dashboard/, desktop-linux/, desktop-mac/,
  mobile-android/, agents/, tests/, scripts/, docs/, assets/screenshots/.
- goal.md, design.md, handoff.md, UNLICENSE created. No license file.
- GitHub repo target: Anonyoumss/internet-dream (public, Pages via Actions).

### Phase 2 — Core Engine & Ingestion (in progress)
- [ ] Encrypted store + FTS5 index
- [ ] WhatsApp + DiscordChatExporter parsers
- [ ] LLM gateway (OpenAI-compat + Anthropic + Ollama)
- [ ] FastAPI app + CLI

### Phase 3 — Cross-Platform UIs (pending)
- [ ] Web dashboard (Material 3)
- [ ] PyQt6 Linux client
- [ ] SwiftUI Liquid Glass macOS client + dmg script
- [ ] Compose Material 3 Android app

### Phase 4 — Tests, Screenshots, Docs, Ship (pending)
- [ ] pytest green locally + CI
- [ ] Screenshots → assets/screenshots/
- [ ] README (Focus-Plan style)
- [ ] Push, enable Pages, verify live URL

## Environment notes
- Python 3.14, Node 24, qmake/cmake present. No PyQt6/Android SDK locally —
  native builds happen in GitHub Actions.
