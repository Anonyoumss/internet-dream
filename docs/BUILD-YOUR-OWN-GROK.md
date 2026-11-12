# Build Your Own Grok — The Complete Course

*A senior-engineer walkthrough of building a personal AI assistant from
scratch. Every module has plain-English explanations, real code, and a
hands-on exercise so you know it works.*

> Note: you said "do all mods in 1 pass" — so here is the whole roadmap
> in one document. Read it top to bottom, or jump to any module.

---

## Module 1 — Architecture Overview

### The real-world analogy

Think of the AI assistant as a **restaurant**:

| Part of the system | Restaurant equivalent | What it does |
|---|---|---|
| **Frontend** (web/app UI) | The dining room + menu | Where you sit, read the menu, tell the waiter what you want |
| **Backend** (server) | The waiter + kitchen pass | Takes your order, carries it to the kitchen, brings back the food |
| **AI Model** (the "brain") | The head chef | Actually cooks — turns your order into a dish (an answer) |
| **Tools** (search, browser, APIs) | The pantry + suppliers | The chef can't make every dish from memory — tools fetch ingredients (live web data) |
| **Channels** (Telegram/Discord/etc.) | Drive-through / delivery apps | Alternative ways customers can order without visiting the dining room |

### The text diagram

```
   YOU                         THE SYSTEM
   ───                         ──────────
┌──────────┐   "what's the     ┌─────────────────────────────────────┐
│ Web chat │   weather?"       │            BACKEND (FastAPI)        │
│ Telegram │ ────────────────► │                                     │
│ Discord  │   HTTPS request   │   1. receive message                 │
│ WhatsApp │                   │   2. figure out if tools are needed │
└──────────┘                   │   3. ask the BRAIN for an answer    │
                               │   4. run tools if the brain asks    │
                               │   5. send the final answer back     │
                               └──────────────┬──────────────────────┘
                                              │ HTTP request
                                              ▼
                                     ┌─────────────────┐
                                     │   THE BRAIN     │
                                     │  (AI model)     │
                                     │  Ollama / xAI / │
                                     │  OpenAI / etc.  │
                                     └────────┬────────┘
                                              │ "I need to search"
                                              ▼
                                     ┌─────────────────┐
                                     │     TOOLS       │
                                     │ web search,     │
                                     │ browser, APIs   │
                                     └─────────────────┘
```

### Jargon, defined

- **API** (Application Programming Interface): a menu of things one
  program can ask another program to do. `GET /search?q=cat` means
  "please run the search function with q=cat."
- **HTTP / HTTPS**: the language browsers and apps use to talk to
  servers. HTTPS is the encrypted version.
- **JSON**: the universal data format — `{"name": "Ali", "age": 20}`.
  Almost every API speaks JSON.
- **Localhost / 127.0.0.1**: "this computer." When your backend runs on
  your laptop, `http://127.0.0.1:8000` means *your* machine, port 8000.
- **Port**: a numbered door on your computer. Different apps listen on
  different ports (8000, 8765, 3000…).
- **Endpoint / route**: one specific URL+action on a server, e.g.
  `POST /chat` = "accept a chat message here."
- **Webhook**: a URL a service (Telegram, Discord) calls *on your
  behalf* when something happens — e.g., someone messages your bot and
  Telegram POSTs the message to your backend.
- **Function calling / tools**: the AI doesn't run code itself. It
  *asks* your backend to run a named function ("search the web for X"),
  your backend runs it, feeds the result back, and the AI writes the
  final answer.
- **Prompt**: the text you send to the AI. The "system prompt" is hidden
  instructions that shape its personality.

### The one-sentence version

> The frontend collects your words → the backend decides what to do →
> the brain writes the answer → tools fetch anything live the brain
> can't know → channels are just extra frontends.

### ✅ Exercise 1 — verify the pieces exist on your machine

```bash
# 1. You already have a backend: Internet's Dream
cd "internet-dream"
.venv/bin/dream serve          # leave running → http://127.0.0.1:8765
curl http://127.0.0.1:8765/health
# expected: {"ok":true,"docs":...}

# 2. Check the brain — is Ollama installed?
which ollama || echo "not installed — see Module 2"
```

---

## Module 2 — The Brain: Running AI Locally

### Cloud vs. local — honest comparison

| | Cloud (xAI Grok, OpenAI, Gemini) | Local (Ollama, llama.cpp) |
|---|---|---|
| Quality | Best models, always latest | Good small models; needs a decent GPU/RAM |
| Privacy | Your prompts leave your machine | Everything stays on your disk |
| Cost | Per-token billing / subscriptions | Free after hardware |
| Offline | Needs internet | Works offline |
| Setup | Paste an API key | Download a ~4–8 GB model once |

**Rule of thumb:** build against the *OpenAI-compatible API shape*
(`POST {base}/chat/completions` with `messages`). Ollama, llama.cpp,
xAI, OpenAI, and Gemini's compat endpoint all speak it — so swapping
brains is a config change, not a rewrite. (This is exactly what
`core/dreamcore/llm.py` does.)

### Option A — Ollama (local, free)

```bash
# install: https://ollama.com/download  (or: curl -fsSL https://ollama.com/install.sh | sh)
ollama pull llama3.1:8b          # ~4.7 GB — good quality/size balance
ollama serve                     # starts on http://localhost:11434

# test it directly:
curl http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.1:8b","messages":[{"role":"user","content":"Say hi in one word"}]}'
```

Point any OpenAI-compatible client at `http://localhost:11434/v1` —
that's it. No API key needed (send any string or omit the header).

### Option B — xAI (Grok's actual API)

Grok is cloud-only — there is no local Grok. You get an API key at
<https://console.x.ai>, then:

```bash
curl https://api.x.ai/v1/chat/completions \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"grok-3-mini","messages":[{"role":"user","content":"hi"}]}'
```

Same request shape as Ollama — different `base_url`, `api_key`, `model`.

### Wire it into your backend

```bash
# local brain:
dream config --provider openai-compatible \
  --base-url http://localhost:11434/v1 --model llama3.1:8b

# or cloud brain:
dream config --provider openai-compatible \
  --base-url https://api.x.ai/v1 --api-key xai-... --model grok-3-mini
```

### ✅ Exercise 2 — prove the brain works

```bash
curl -X POST http://127.0.0.1:8765/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"what is 2+2?"}'
# You should get a real generated answer (needs a configured provider).
# With no provider it degrades to raw memory matches — that's by design.
```

---

## Module 3 — The Nervous System: Backend

You already have one — `core/dreamcore/api.py` (FastAPI). Let's learn
what each piece does by reading a minimal version of the same idea.

### Minimal backend from scratch (~40 lines)

```python
# brain_server.py — run: uvicorn brain_server:app --port 8000
from fastapi import FastAPI
from pydantic import BaseModel
import httpx

app = FastAPI()

class ChatIn(BaseModel):            # pydantic = automatic validation:
    message: str                     # if "message" isn't a string → 422

@app.post("/chat")                  # route = "POST requests to /chat"
def chat(body: ChatIn):
    # forward to the brain (Ollama shown; swap base_url for xAI/OpenAI)
    r = httpx.post("http://localhost:11434/v1/chat/completions", json={
        "model": "llama3.1:8b",
        "messages": [{"role": "user", "content": body.message}],
    }, timeout=120)
    answer = r.json()["choices"][0]["message"]["content"]
    return {"answer": answer}

@app.get("/health")                 # GET /health → {"ok": true}
def health():
    return {"ok": True}
```

Line-by-line:

1. `BaseModel` — tells FastAPI the expected JSON shape. Send
   `{"message": 42}` and it rejects before your code runs.
2. `@app.post("/chat")` — decorator = "when a POST hits /chat, run this."
3. `httpx.post(...)` — the backend is just an HTTP *client* to the brain.
   Backend↔brain is the same protocol as browser↔backend.
4. `choices[0].message.content` — unwrapping the standard OpenAI-style
   response envelope.

### What your real backend adds on top

- `Store` — encrypted SQLite (AES-256-GCM payloads + FTS5 search index)
- `agent.py` — the tool-calling loop (Module 5)
- `/sync`, `/ingest*`, `/auth/*` — connectors and OAuth

### ✅ Exercise 3 — run the minimal server

```bash
pip install fastapi uvicorn httpx
uvicorn brain_server:app --port 8000 &
curl http://localhost:8000/health          # → {"ok":true}
curl -X POST localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello"}'
```

---

## Module 4 — The Face: Frontend

A chat UI is ~60 lines of HTML/CSS/JS. Save as `chat.html` and open it —
it talks to `brain_server.py` on port 8000 (or `dream serve` on 8765 by
changing one string).

```html
<!doctype html><meta charset="utf-8"><title>My Grok</title>
<style>
  body{font-family:system-ui;max-width:640px;margin:40px auto;padding:0 16px}
  #log{border:1px solid #ddd;border-radius:12px;padding:16px;min-height:300px}
  .me{color:#6d4bd8}.ai{color:#222}
  #box{display:flex;gap:8px;margin-top:12px}
  input{flex:1;padding:12px;border-radius:10px;border:1px solid #ccc}
  button{padding:12px 20px;border:0;border-radius:10px;background:#6d4bd8;color:#fff;cursor:pointer}
</style>
<h2>My Grok 🧠</h2>
<div id="log"></div>
<div id="box">
  <input id="msg" placeholder="Say something…" autofocus>
  <button onclick="send()">Send</button>
</div>
<script>
const API = "http://localhost:8000";   // ← your backend
const log = document.getElementById("log");
const inp = document.getElementById("msg");

function add(cls, text){
  const d = document.createElement("div");
  d.className = cls; d.textContent = text;
  log.appendChild(d); log.scrollTop = log.scrollHeight;
}

async function send(){
  const message = inp.value.trim(); if(!message) return;
  inp.value = ""; add("me", "You: " + message);
  const r = await fetch(API + "/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message})
  });
  const data = await r.json();
  add("ai", "AI: " + data.answer);
}
inp.addEventListener("keydown", e => e.key === "Enter" && send());
</script>
```

What's happening:

- `fetch()` — the browser's HTTP client. `POST` + JSON body = same as
  `curl -X POST` in Module 3.
- `JSON.stringify` / `jsonDecode` — the JSON format from Module 1.
- The page is *static* — no server needed to host it. Double-click the
  file or `python3 -m http.server`.

> You already have a much nicer version of this: the Material 3
> dashboard at `web-dashboard/` (Chat page → `POST /chat`).

### ✅ Exercise 4 — run the UI

```bash
# backend running (dream serve or brain_server.py), then:
xdg-open chat.html        # or drag into Chrome
# type a message → you should see the AI reply appear.
```

---

## Module 5 — The Eyes: Tools / Function Calling

The brain can't know today's weather or your files — so we let it
*request* actions. The flow:

```
you: "search the web for Flutter news"
  → backend sends to brain WITH the tool list
  → brain replies: {"tool_calls": [{"name": "web_search",
                                    "arguments": {"q": "Flutter news"}}]}
  → backend RUNS web_search("Flutter news") → gets results
  → backend sends results back to brain: "tool said: ..."
  → brain writes the final answer using those results
```

### The tool definition (what the brain sees)

```python
TOOLS = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the live web for current information.",
        "parameters": {
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
        },
    },
}]
```

### The dispatcher (what your backend runs)

```python
def run_tool(name: str, args: dict) -> str:
    if name == "web_search":
        r = httpx.get("https://duckduckgo.com/html/",
                      params={"q": args["q"]}, timeout=20)
        # strip tags → return first ~2000 chars of results
        import re
        text = re.sub(r"<[^>]+>", " ", r.text)
        return re.sub(r"\s+", " ", text)[:2000]
    return f"unknown tool {name}"
```

### The loop (the important part)

```python
convo = [{"role": "user", "content": user_message}]
for _ in range(5):                      # max 5 tool rounds
    msg = call_brain(convo, tools=TOOLS)   # returns assistant message
    if not msg.get("tool_calls"):          # brain is done → final answer
        return msg["content"]
    convo.append(msg)                      # keep the tool_call request
    for tc in msg["tool_calls"]:
        result = run_tool(tc["function"]["name"],
                          json.loads(tc["function"]["arguments"]))
        convo.append({"role": "tool",
                      "tool_call_id": tc["id"],
                      "content": result})  # feed result back
```

**This is literally what `dreamcore/agent.py` already implements** —
its tools are `search_memory`, `remember`, `sync_source`, `get_stats`,
`list_sources` instead of `web_search`. Same pattern, your data.

### Adding a real browser (Playwright)

```python
from playwright.sync_api import sync_playwright

def browse(url: str) -> str:
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(url, timeout=20000)
        return page.inner_text("body")[:4000]   # visible text only
```

Expose it as a `read_page` tool. Note: headless browsing of arbitrary
sites can hit bot-detection — for robust scraping prefer official APIs.

### ✅ Exercise 5 — test tool calling

```bash
# your agent already has tools — ask it to use one:
curl -X POST http://127.0.0.1:8765/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"sync my browser history source then tell me how many memories I have"}'
# watch "steps" in the response — you'll see sync_source + get_stats calls
```

---

## Module 6 — The Channels: Messaging Apps

Your backend can *be* a bot on Telegram/Discord/WhatsApp. Two patterns:

### Pattern A — Long polling (simpler, what you have)

Backend repeatedly asks the platform "anything new?" — Telegram Bot API
`getUpdates`, Discord gateway, etc. `dream telegram-bot` and
`tg_user.py` (Telethon userbot) work this way. No public URL needed —
works behind NAT/localhost.

### Pattern B — Webhooks (what big bots use)

The platform POSTs events to a public URL you give it:

```
someone messages your Telegram bot
  → Telegram servers POST {"message": {...}} to https://you.ngrok.io/hook
  → your FastAPI route @app.post("/hook") runs → replies via sendMessage
```

Needs a public URL (ngrok/cloudflare tunnel in dev). Webhooks scale
better but add ops complexity — start with polling.

### Telegram bot in ~20 lines (python-telegram-bot)

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

async def on_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # → forward to your brain, reply with the answer
    r = httpx.post("http://127.0.0.1:8765/ask",
                   json={"question": text}, timeout=120)
    await update.message.reply_text(r.json()["answer"])

app = Application.builder().token("BOT_TOKEN_FROM_BOTFATHER").build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_msg))
app.run_polling()
```

### Discord bot (discord.py)

```python
import discord, httpx

class Bot(discord.Client):
    async def on_message(self, msg):
        if msg.author == self.user or not msg.content: return
        r = httpx.post("http://127.0.0.1:8765/ask",
                       json={"question": msg.content}, timeout=120)
        await msg.reply(r.json()["answer"][:1900])  # discord msg limit

Bot(intents=discord.Intents.default()).run("DISCORD_BOT_TOKEN")
```

### WhatsApp

- **Bot API** (official, business accounts only): webhook-based, free tier.
- **User-side bridge**: your `whatsapp-bridge/` (Baileys) already does
  this — it *receives* messages and indexes them. Two-way "bot that
  replies" on a normal account risks a ban; official Cloud API is the
  safe path for replies.

> Your repo already implements all of this: `telegram_bot.py` (commands
> /ask /search /export /sync), `tg_user.py` (full-account userbot),
> `discord_api.py` (read-only export), `whatsapp-bridge/` (live inbound).

### ✅ Exercise 6 — wire one channel

Pick the easiest: Telegram.

```bash
# 1. @BotFather → /newbot → copy token
dream config --telegram-token 123456:ABC...
# 2. run the bridge (leave it running)
dream telegram-bot
# 3. in Telegram, message your bot:  /stats
# 4. you should get your memory stats back — no code written, it works.
```

---

## Capstone — How it all fits (your actual system)

```
WhatsApp bridge ─┐
Telegram bot ────┤
Discord export ──┤        ┌──────────────┐
Chrome history ──┼───────►│ dream serve  │◄──── web dashboard (M3 Expressive)
Files/Drive/Gmail│        │  FastAPI     │◄──── Qt6 desktop app
YouTube Takeout ─┘        │  + agent.py  │◄──── Flutter/Compose mobile
                          │  + store     │◄──── browser extension
                          └──────┬───────┘
                                 │ HTTP
                          ┌──────▼───────┐
                          │  THE BRAIN   │  Gemini 2.5 Flash (your key)
                          │  (swappable) │  or Ollama / xAI / OpenAI
                          └──────────────┘
```

Every arrow you saw in this course exists in the repo. The course
taught you to build each piece; the repo is those pieces assembled.

## What's next (in order of fun)

1. Run `ollama pull llama3.1:8b` → point `dream config` at it → your
   second brain works with **zero cloud dependency**.
2. Add a `web_search` tool to `agent.py`TOOLS — 30 lines, teaches you
   tool-calling deeper.
3. Read `core/dreamcore/store.py` — see how AES-256-GCM + FTS5 works.
4. Build the Flutter/Qt apps' chat screens against `/chat` (in progress).
