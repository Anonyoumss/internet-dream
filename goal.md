# Goal — Internet's Dream (Universal Contextual Memory)

Build a private, locally-encrypted personal second brain that indexes a user's
digital life (chat exports, email, calendar, photos metadata) and answers
questions like "what was that restaurant my friend recommended last month?".

## Success criteria

- [x] Local encrypted store (AES-256-GCM at rest, zero telemetry)
- [x] Ingestion: WhatsApp chat export + DiscordChatExporter JSON
- [x] LLM gateway: OpenAI-compatible (OpenAI/Gemini/Ollama) + Anthropic
- [x] FastAPI backend (`dreamcore serve`) with ingest/search/ask/stats/graph
- [x] Web dashboard (Material 3) deployed to GitHub Pages, demo mode offline
- [x] Linux desktop client (Qt / PyQt6)
- [x] macOS desktop client (SwiftUI, "Liquid Glass") + unsigned .dmg via CI
- [x] Android app (Jetpack Compose, Material 3) debug APK via CI
- [x] Agent orchestrator (planner/coder/reviewer) reading goal/design/handoff
- [x] Tests pass in CI; screenshots in assets/screenshots/
- [x] README styled after Anonyoumss/Focus-Plan; no license file
- [x] Repo: github.com/Anonyoumss/internet-dream, Pages enabled
