# Handoff — Internet's Dream

## Phase log

### Phase 1 — Initialization & Scaffold (done)
- Repo scaffolded: core/, web-dashboard/, desktop-linux/, desktop-mac/,
  mobile-android/, agents/, tests/, scripts/, docs/, assets/screenshots/.
- goal.md, design.md, handoff.md, UNLICENSE created. No license file.
- GitHub repo: github.com/Anonyoumss/internet-dream (public).

### Phase 2 — Core Engine & Ingestion (done)
- dreamcore.store: SQLite + AES-256-GCM payloads + FTS5 + vector blobs,
  hybrid RRF search, thread-safe for FastAPI threadpool.
- Ingest: WhatsApp _chat.txt (multi-locale, continuations, system-msg
  filter) + DiscordChatExporter JSON.
- Embed: offline hashing embedder (default) + OpenAI-compatible API embedder.
- LLM gateway: OpenAI-compatible + Anthropic; config at
  ~/.internet-dream/config.json.
- FastAPI app + `dream` CLI. Verified end-to-end locally:
  ingest 7 docs → search/ask/graph/stats all return data.

### Phase 3 — Cross-Platform UIs (done)
- web-dashboard: Material 3 SPA, demo mode + live mode, PWA manifest.
- desktop-linux: PyQt6 client + run.sh + requirements.
- desktop-mac: SwiftUI Liquid Glass (macOS 26 glassEffect, material
  fallback) + scripts/build-mac-dmg.sh.
- mobile-android: Compose Material 3 app, 4 tabs, LAN/emulator API config.

### Phase 4 — Tests, Screenshots, Docs, Ship (done)
- pytest: 8/8 pass locally and in CI.
- Screenshots: web-{dashboard,search,ask,graph,settings,phone}.png in
  assets/screenshots/ (headless Chrome, demo mode).
- README in Focus-Plan style; UNLICENSE; no LICENSE file.
- Pushed; all workflows green:
  CI ✅ · Pages ✅ (live at anonyoumss.github.io/internet-dream) ·
  Android APK ✅ (15MB artifact) · macOS DMG ✅ (verified valid UDZO) ·
  Linux tarball ✅.
- Fixes applied in CI: AndroidX gradle.properties, SwiftUI .onAppear
  placement, ExperimentalMaterial3Api opt-in.

## Phase 5 — Universal source coverage (done)
- sources/: google_auth (InstalledAppFlow, token.json 0600), gmail
  (full-mime parse, html→text fallback), calendar (events ±365d),
  photos (Picker API sessions, metadata-only), browser (Chrome/Firefox
  history via temp-copy sqlite), files (text ext walk + chunking).
- sync.py registry + batched embed/store; CLI: auth/sync/sources;
  API: GET /sources, POST /sync.
- pyproject extra `google` for google-api-python-client stack.
- Tests: 19/19 pass (parser-level, no network). Smoke-tested
  `dream sync files` + `POST /sync` end-to-end.

## Phase 6 — Telegram, YouTube, Drive, backend OAuth (done)
- sources/telegram.py: Bot API getUpdates → Documents; download_file,
  send_document, send_message helpers.
- dreamcore/telegram_bot.py: `dream telegram-bot` long-poll bridge —
  /ask /search /stats /remember /export (sends .md file) /sync, auto-
  ingests documents/photos to ~/.internet-dream/inbox/.
- sources/youtube.py: Takeout watch-history.html + JSON activity parser.
- sources/drive.py: Drive v3 metadata + text-file content indexing.
- dreamcore/oauth.py + API: GET /auth/google/start|callback|status —
  backend-managed consent, token shared by all clients; dashboard
  Settings has "Connect Google account" button.
- SCOPES extended: +drive.readonly +youtube.readonly; token re-consent
  on scope change.
- CLI: `dream config --telegram-token`, `dream telegram-bot`.
- Tests: 27/27 pass.

## Phase 7 — Telegram userbot (Telethon, real account) (done)
- tg_user.py: Telethon client (session ~/.internet-dream/telegram_user.
  session), api_id/api_hash via config/env, message_to_document mapper,
  iter_account_messages + sync_account (async, batched), userbot_loop —
  Saved Messages (or --chat) command bridge reusing telegram_bot.
  handle_update; file download→index; /export sends .md via send_file.
- CLI: tg-login (interactive phone/code/2FA), tg-sync, tg-bot --chat.
- config.json: telegram_api_id/hash fields; pyproject [telegram] extra.
- Tests: 31/31 pass.

## Phase 8 — Real-machine validation + Discord API source (in progress)
- Verified on real data (read-only, no messages sent):
  - browser sync: 13,071 Chrome history docs (incl. YouTube visits)
  - files sync: Downloads + Documents → 6,969 chunks (incl. Zoom/Tamayuz
    meeting transcripts)
  - `dream serve` live on 127.0.0.1:8765 → 20,040+ docs; Gemini
    (gemini-2.5-flash) /ask answers with real citations.
- sources/discord_api.py: read-only Discord REST export — user token
  from ~/.internet-dream/discord_token.txt (0600) or config
  discord_token; GET /users/@me/guilds → channels → messages, 429-aware,
  optional include_dms + guild filter. Registered as `discord` source.
- Tests: 34/34 pass.
- Discord sync running against 35 real guilds (max 300 msgs/channel).

## Phase 9 — Agent chat + onboarding + WhatsApp source (done)
- dreamcore/agent.py: tool-calling loop (search_memory, remember,
  sync_source, get_stats, list_sources) over OpenAI-compatible function
  calling; graceful degradation for anthropic/no-tools providers.
- API: POST /chat {message, history} → {answer, steps, sources};
  POST /ingest-upload (multipart .txt/.json → ~/.internet-dream/inbox/).
- sources/whatsapp.py: scans a folder for WhatsApp _chat.txt exports.
- Dashboard: Ask → Chat (conversation UI + tool-step chips), new Setup
  wizard page (#/setup: API key → Google → sources → Telegram → chat),
  Sources page export-upload control. Nav updated.
- pyproject: +python-multipart.
- Tests: 36/36 pass. Live-verified: /chat answered stats + Discord
  questions via real tool calls (Gemini 2.5 Flash).
- whatsapp-bridge/ (Baileys): QR-link real account, read-only inbound
  indexing to /ingest-text, media → ~/.internet-dream/whatsapp-media/.
  Verified QR generation; needs one user scan to activate.
- Material 3 Expressive reskin: spring motion, 28-36px radii, gradient
  surfaces/type, elevated cards — web-dashboard/styles.css rewritten,
  manifest colors updated. Verified render via headless Chrome.
- Live agent verified end-to-end: remember/search/sync tools write and
  read the real store (agent source docs present).
- Real store: ~63k docs (browser 13,071 · discord 43,100+ and climbing ·
  files 6,969 · agent 1).

## Known gaps / next actions
- Google sources need client_secret.json + one consent (web or CLI).
- Telegram userbot needs api_id/api_hash + interactive login (can't
  automate the SMS/code step); bot mode covers token-only setups.
- YouTube needs a Takeout export (no API for watch history).
- Photos indexes metadata only by design (Picker API, no binary download).
- Photos indexes metadata only by design (Picker API, no binary download).
- Native clients are thin shells over `dream serve`; not device-tested.
- macOS DMG unsigned (ad-hoc) — Gatekeeper warning expected.
- Android artifact is debug-signed only.
- Orchestrator is a guarded scaffold; extend ALLOW list carefully.
