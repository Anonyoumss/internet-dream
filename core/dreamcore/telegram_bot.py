"""Telegram bot bridge — `dream telegram-bot`.

Long-polls getUpdates and turns the bot into a remote control for your
memory:

  /start, /help          — commands
  /stats                 — corpus stats
  /search <query>        — hybrid search, top 5
  /ask <question>        — retrieve + LLM answer (or raw matches offline)
  /remember <text>       — save a memory manually
  /export <query>        — send matching memories back as a .md file
  any other text         — saved as a memory in chat "telegram-dm"
  documents/photos       — downloaded to ~/.internet-dream/inbox/ and
                           indexed if text-readable

Requires a bot token (BotFather) via `dream config --telegram-token`.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..embed import get_embedder
from ..llm import LLMGateway
from ..store import Document, Store
from . import telegram
from .sync import sync_source

_INBOX = Path.home() / ".internet-dream" / "inbox"
_DB = Path.home() / ".internet-dream" / "memory.sqlite3"

HELP = """Internet's Dream bot commands:
/ask <question> — ask your memory (LLM if configured)
/search <query> — find memories
/stats — corpus stats
/remember <text> — save a note
/export <query> — get matches as a .md file
/sync files path=<dir> — index a folder
/sendfile — (send me a document/photo to index it)
Anything else is saved as a memory."""


def _store() -> Store:
    return Store(_DB)


def _answer_question(store, embedder, question: str) -> str:
    hits = store.hybrid_search(question, embedder.embed(question), 8)
    if not hits:
        return "I don't have anything indexed about that yet."
    try:
        gw = LLMGateway()
        context = "\n\n".join(
            f"[{h.title} · {h.sender or '?'}]\n{h.snippet}" for h in hits)
        return gw.chat([
            {"role": "system", "content":
             "You are the memory core of Internet's Dream. Answer using "
             "ONLY the memories given. Cite sources by title."},
            {"role": "user", "content": f"Memories:\n{context}\n\nQ: {question}"},
        ])
    except Exception:
        return "\n".join(f"• {h.title}: {h.snippet[:120]}" for h in hits[:5])


def _export_matches(store, embedder, query: str, chat_id) -> str:
    hits = store.hybrid_search(query, embedder.embed(query), 10)
    if not hits:
        return "no matches"
    lines = [f"# Internet's Dream export — {query}", ""]
    for h in hits:
        doc = store.get(h.doc_id)
        lines += [f"## {doc['title']}",
                  f"_{doc.get('sender') or '?'} · {doc.get('source')} · "
                  f"{time.strftime('%Y-%m-%d', time.localtime(doc['ts'])) if doc.get('ts') else ''}_",
                  "", doc.get("text", "")[:4000], "", "---", ""]
    out = _INBOX / f"export-{int(time.time())}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    telegram.send_document(chat_id, out,
                           caption=f"{len(hits)} memories matching '{query}'")
    return f"sent {len(hits)} memories as file ✓"


def _ingest_file(msg: dict, store, embedder) -> str:
    """Download a document/photo sent to the bot and index it."""
    doc = msg.get("document") or {}
    photo = msg.get("photo") or []
    if doc:
        file_id, name = doc["file_id"], doc.get("file_name", "file")
    elif photo:
        file_id, name = photo[-1]["file_id"], "photo.jpg"
    else:
        return "no file found"
    dest = telegram.download_file(file_id, _INBOX)
    # index text-readable files; otherwise store metadata only
    p = Path(dest)
    try:
        text = p.read_text(encoding="utf-8")
        if len(text) < 2_000_000:
            d = Document(source="telegram", kind="file",
                         title=f"📎 {name}", text=text,
                         sender="telegram", chat="telegram-files",
                         ts=time.time(),
                         metadata={"path": str(p)})
            store.add(d, embedder.embed(f"{d.title}\n{text[:4000]}"))
            return f"indexed '{name}' ({len(text)} chars) ✓"
    except (UnicodeDecodeError, OSError):
        pass
    d = Document(source="telegram", kind="file",
                 title=f"📎 {name}",
                 text=f"[binary file saved: {p}] size={p.stat().st_size}B",
                 sender="telegram", chat="telegram-files",
                 ts=time.time(), metadata={"path": str(p)})
    store.add(d, embedder.embed(d.title))
    return f"saved '{name}' to inbox (binary — metadata indexed) ✓"


def handle_update(u: dict, store: Store, embedder) -> str | None:
    """Process one update; returns a reply string or None."""
    msg = u.get("message") or {}
    if not msg:
        return None
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()

    if msg.get("document") or msg.get("photo"):
        try:
            return _ingest_file(msg, store, embedder)
        except Exception as e:
            return f"file ingest failed: {e}"

    if not text:
        return None

    if text.startswith("/"):
        cmd, _, arg = text.partition(" ")
        cmd, arg = cmd.lower(), arg.strip()
        try:
            if cmd in ("/start", "/help"):
                return HELP
            if cmd == "/stats":
                s = store.stats()
                return (f"{s['total']} memories · "
                        + ", ".join(f"{k}:{v}" for k, v in s["by_source"].items()))
            if cmd == "/search":
                hits = store.hybrid_search(arg, embedder.embed(arg), 5)
                return "\n".join(
                    f"• {h.title}: {h.snippet[:120]}" for h in hits) or "no results"
            if cmd == "/ask":
                return _answer_question(store, embedder, arg)
            if cmd == "/remember":
                d = Document(source="telegram", kind="note",
                             title="✈ telegram note", text=arg,
                             sender="telegram", chat="telegram-dm",
                             ts=time.time())
                store.add(d, embedder.embed(arg))
                return "remembered ✓"
            if cmd == "/export":
                return _export_matches(store, embedder, arg, chat_id)
            if cmd == "/sync":
                parts = arg.split()
                if not parts:
                    return "usage: /sync <source> [key=value ...]"
                name = parts[0]
                opts = {}
                for kv in parts[1:]:
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        try: v = int(v)
                        except ValueError:
                            try: v = float(v)
                            except ValueError: pass
                        opts[k] = v
                n = sync_source(store, embedder, name, opts)
                return f"synced {n} documents from {name} ✓"
            return "unknown command — /help"
        except Exception as e:
            return f"error: {e}"

    # plain text → save as memory
    d = Document(source="telegram", kind="message",
                 title="✈ telegram", text=text,
                 sender="telegram", chat="telegram-dm", ts=time.time())
    store.add(d, embedder.embed(text))
    return "saved to memory ✓ (use /ask or the dashboard to query it)"


def run(poll_timeout: int = 30):
    if not telegram.bot_token():
        raise SystemExit("no telegram bot token — `dream config --telegram-token 123:abc`")
    store = _store()
    embedder = get_embedder()
    offset = None
    print("telegram bot running — Ctrl+C to stop")
    while True:
        try:
            updates = telegram.get_updates(offset=offset, timeout=poll_timeout)
        except Exception as e:
            print(f"poll error: {e} — retrying in 5s")
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            try:
                reply = handle_update(u, store, embedder)
            except Exception as e:
                reply = f"error: {e}"
            if reply:
                try:
                    telegram.send_message(u["message"]["chat"]["id"], reply)
                except Exception as e:
                    print(f"send error: {e}")
