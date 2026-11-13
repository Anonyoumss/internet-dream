# Internet's Dream — Marketing Kit

All copy is ready to paste. Swap `{LINK}` for your Pages URL or release URL.

---

## Taglines

- **Your entire digital life — indexed, encrypted, searchable.**
- **50 apps. One memory. Zero cloud.**
- **The second brain that never forgets — and never leaves your device.**
- **Ask it anything. It remembers everything.**

## Elevator pitch (2 sentences)

> Internet's Dream is a private, locally-encrypted second brain for your
> digital life. It indexes your Gmail, Calendar, Discord, Telegram,
> WhatsApp, YouTube, browser history, and files — then lets you chat with
> an AI agent that can search it all, sync it, and act on it.

## Long description (store listings / about pages)

Your life is scattered across 50 apps — notes, chats, bookmarks,
screenshots, emails. Finding that one thing you saw three weeks ago is
nearly impossible.

**Internet's Dream fixes that.** It builds a private, encrypted index of
your digital life and gives you an AI agent that actually knows you.

**What it indexes**
- Gmail, Google Calendar, Google Drive, Google Photos (read-only OAuth)
- Discord servers (live, read-only export)
- Telegram — bot mode or full account via userbot
- WhatsApp — live bridge or chat exports
- YouTube watch/search history (Takeout)
- Chrome & Firefox browsing history
- Any folder of files — chunked and searchable

**What you can do**
- **Chat** — ask anything; the agent searches your memories and cites sources
- **Deep Research** — multi-step reports from your memories + the live web
- **Automations** — scheduled agent jobs that run while you sleep
- **Voice** — speak to it, hear answers (Whisper + neural TTS)
- **Vision** — send photos, it describes and remembers them
- **Export/Forget** — GDPR export of everything, or delete any memory

**Privacy, actually**
- AES-256-GCM encrypted at rest — payloads are ciphertext, always
- Search index stores metadata only (sender, chat, date)
- Hashing embedder works fully offline; optional API embeddings
- LLM calls send only retrieved snippets, never your whole life
- Zero telemetry. No account. No cloud sync of your memories.

**Open source.** No license — do whatever you want.
{LINK}

---

## Email templates

### 1 — Launch announcement (cold/waitlist)

**Subject:** I built a second brain for my digital life — it indexes everything

Hey {name},

Quick context: I got tired of "I know I saved that somewhere" — Gmail,
Discord, 40 browser tabs, WhatsApp chats, YouTube history — and built
**Internet's Dream**: a private, encrypted index of your entire digital
life with an AI agent on top.

What makes it different from Notion AI / Rewind / Limitless:
- **Local-first** — your memories are AES-256-GCM encrypted on YOUR
  machine. No cloud copy of your life.
- **Actually agentic** — it doesn't just search; it can sync sources,
  run scheduled jobs, browse the web, transcribe voice, see images.
- **Every app** — Gmail, Calendar, Drive, Discord, Telegram, WhatsApp,
  YouTube, browser history, files. One consent for Google, QR-scan for
  WhatsApp.
- **Free & open** — no license, no account, no subscription.

It's live: {LINK}
Dashboard runs in your browser; Android APK + macOS/Linux builds in CI.

Would love your take — reply with what's missing for YOUR workflow.

— {you}

### 2 — Feature drop (existing users)

**Subject:** New in Dream: deep research, voice, automations 🧠

Hey {name},

Shipped this week:

🔬 **Deep Research** — ask a big question; the agent plans sub-queries,
searches your memories AND the live web, and writes a cited report.

🎙 **Voice** — click the mic in Chat, speak, it transcribes (Whisper)
and answers. Hit "listen" on any answer for neural TTS.

⏰ **Automations** — schedule agent prompts ("daily recap of my
activity", "sync Discord every hour"). They run inside the backend —
your second brain works while you sleep.

👁 **Vision** — send a photo to the Telegram/WhatsApp bot; it describes
it and indexes the description as a searchable memory.

Plus: GDPR export (.md of everything), one-click forget, web search +
page-reading tools for the agent.

Try it: {LINK} → Chat page.

### 3 — Re-engagement (dormant)

**Subject:** Your memories miss you (they're still encrypted, promise)

Hey {name},

It's been a while — your encrypted store hasn't moved. Quick wins to
get back in:

1. `dream serve` → open {LINK}
2. Chat: "sync my discord and browser sources" — the agent does it for you
3. Ask it something only YOUR data could answer — that's the magic moment

New since you left: deep research mode, voice in/out, scheduled
automations, and a Flutter Android app.

— {you}

---

## Social posts

### X / Twitter thread

**1/**
I got tired of "I know I saved that somewhere."

So I built Internet's Dream — a private, encrypted second brain for my entire digital life.

Gmail. Discord. Telegram. WhatsApp. YouTube. Browser history. Files.
One index. One AI agent. Zero cloud.

Thread 🧵

**2/**
The problem: my life lives in 50 apps. Finding that one thing I saw 3 weeks ago? Impossible.

Bookmarks, chats, screenshots, emails — all siloed, all unsearchable together.

**3/**
Dream indexes ALL of it into an AES-256-GCM encrypted local store. Payloads are ciphertext — the search index only holds metadata (who, when, which chat).

Your life never leaves your machine unless YOU send snippets to an LLM.

**4/**
Then an agent sits on top. Not just search — tools:

🔍 search_memory · 📝 remember · 🔄 sync_source · 🌐 web_search · 📖 read_url · 📊 stats

Ask "what did I work on this week?" and it actually answers, with citations.

**5/**
It gets better:

🔬 Deep Research — plans sub-queries, searches memory + live web, writes cited reports
🎙 Voice — Whisper STT in, neural TTS out
⏰ Automations — scheduled agent jobs that run while you sleep
👁 Vision — send photos, it remembers what it saw

**6/**
Setup is one page: paste an API key → connect Google once → pick sources → chat.

Android APK, macOS DMG, Linux tarball, browser extension, Telegram bot — all thin shells over one backend.

Everything is Material 3 Expressive. Yes, really.

**7/**
Free. Open source. No license. No account. No telemetry.

github.com/Anonyoumss/internet-dream

If you've ever lost a memory to the void — try it. Tell me what's missing.

### Instagram / LinkedIn caption

> Your life is scattered across 50 apps. I built a second brain that indexes ALL of it — encrypted on your device — and an AI agent that can search, sync, research, and act on your memories.
>
> Gmail · Calendar · Drive · Discord · Telegram · WhatsApp · YouTube · browser history · files → one encrypted index → one agent.
>
> Deep research, voice, scheduled automations, vision. Free & open source.
>
> Link in bio 🔗

### Reddit (r/selfhosted, r/opensource, r/privacy)

**Title:** I built a local-first "second brain" that indexes your entire digital life — encrypted, agentic, open source

**Body:**

I was tired of my data being scattered across Gmail, Discord, Telegram, WhatsApp, YouTube history, browser tabs, and files — with no way to ask "what was that thing I saw last month?"

So I built **Internet's Dream**: a FastAPI backend + encrypted SQLite store (AES-256-GCM) + hybrid FTS/vector search + an LLM agent with tools (search_memory, remember, sync_source, web_search, read_url).

Highlights:
- 10+ connectors: Google (one OAuth for Gmail/Cal/Drive/Photos), Discord live export, Telegram userbot (Telethon), WhatsApp bridge (Baileys), YouTube Takeout, browser history, files
- Agent chat with visible tool calls, deep-research mode, scheduled jobs, voice (Whisper+edge-tts), vision
- Clients: Material 3 Expressive web dashboard (GitHub Pages), Flutter Android, Qt6 desktop, MV3 extension, Telegram bot
- CI builds APK/DMG/tarball/extension on every push

Everything runs on localhost; only retrieved snippets go to the LLM. Happy to answer questions — repo in profile.

---

## Press / one-liner

> Internet's Dream is an open-source, local-first personal memory engine:
> it indexes your messages, email, browsing, and files into an
> AES-256-GCM encrypted store and puts a tool-using AI agent on top —
> searchable, schedulable, voice-enabled, and private by design.
