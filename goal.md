# Goal — Internet's Dream (Universal Contextual Memory)

Build a private, locally-encrypted personal second brain that indexes a user's
digital life (chat exports, email, calendar, photos metadata) and answers
questions like "what was that restaurant my friend recommended last month?".

## Success criteria

- [ ] Local encrypted store (AES-256-GCM at rest, zero telemetry)
- [ ] Ingestion: WhatsApp chat export + DiscordChatExporter JSON
- [ ] LLM gateway: OpenAI-compatible (OpenAI/Gemini/Ollama) + Anthropic
- [ ] FastAPI backend (`dreamcore serve`) with ingest/search/ask/stats/graph
- [ ] Web dashboard (Material 3) deployed to GitHub Pages, demo mode offline
- [ ] Linux desktop client (Qt / PyQt6)
- [ ] macOS desktop client (SwiftUI, "Liquid Glass") + unsigned .dmg via CI
- [ ] Android app (Jetpack Compose, Material 3) debug APK via CI
- [ ] Agent orchestrator (planner/coder/reviewer) reading goal/design/handoff
- [ ] Tests pass in CI; screenshots in assets/screenshots/
- [ ] README styled after Anonyoumss/Focus-Plan; no license file
- [ ] Repo: github.com/Anonyoumss/internet-dream, Pages enabled
