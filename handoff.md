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

## Known gaps / next actions
- Gmail/Calendar/Photos adapters not yet implemented (roadmap).
- Native clients are thin shells over `dream serve`; not device-tested.
- macOS DMG unsigned (ad-hoc) — Gatekeeper warning expected.
- Android artifact is debug-signed only.
- Orchestrator is a guarded scaffold; extend ALLOW list carefully.
