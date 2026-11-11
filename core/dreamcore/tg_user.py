"""Telegram *user account* access via Telethon (userbot).

Unlike the Bot API (which only sees chats the bot is in), Telethon logs in
as YOU — full read access to every dialog, send messages, download/upload
files. Requires api_id + api_hash from https://my.telegram.org.

Session file: ~/.internet-dream/telegram_user.session (chmod 600).
Config keys: telegram_api_id, telegram_api_hash (dream config --api-id/--api-hash
or edit ~/.internet-dream/config.json).

Login is interactive: `dream tg-login` → phone → code → 2FA password.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .store import Document

_SESSION_DIR = Path.home() / ".internet-dream"
SESSION = _SESSION_DIR / "telegram_user.session"
CONFIG = _SESSION_DIR / "config.json"


def _config() -> dict:
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text())
        except Exception:
            pass
    return {}


def api_credentials() -> tuple[int, str]:
    cfg = _config()
    aid = os.environ.get("DREAM_TG_API_ID") or cfg.get("telegram_api_id")
    ahash = os.environ.get("DREAM_TG_API_HASH") or cfg.get("telegram_api_hash")
    if not aid or not ahash:
        raise RuntimeError(
            "Telegram userbot needs api_id + api_hash from "
            "https://my.telegram.org → API development tools. "
            "Then: dream config --tg-api-id 12345 --tg-api-hash abcdef")
    return int(aid), str(ahash)


def client():
    """Connected Telethon client (requires prior `dream tg-login`)."""
    try:
        from telethon import TelegramClient
    except ImportError as e:
        raise RuntimeError(
            "Telethon not installed: pip install -e 'core[telegram]'") from e
    api_id, api_hash = api_credentials()
    c = TelegramClient(str(SESSION), api_id, api_hash)
    return c


def is_logged_in() -> bool:
    return SESSION.exists() and SESSION.stat().st_size > 0


def message_to_document(msg, default_chat: str = "") -> Document | None:
    """Pure mapper — works with Telethon Message or any duck-typed object."""
    text = getattr(msg, "raw_text", None) or getattr(msg, "message", "") or ""
    text = text or ""
    media = getattr(msg, "media", None)
    if not text.strip():
        if media is not None:
            kind = type(media).__name__.lower()
            text = f"[{kind} attachment]"
        else:
            return None
    else:
        kind = "message"
    sender = getattr(msg, "sender", None)
    sender_name = "unknown"
    if sender is not None:
        sender_name = (getattr(sender, "first_name", "") or "") + " " + \
            (getattr(sender, "last_name", "") or "")
        sender_name = sender_name.strip() or getattr(sender, "username", "") or "unknown"
    chat = getattr(msg, "chat", None)
    chat_name = getattr(chat, "title", None) or default_chat or "unknown"
    date = getattr(msg, "date", None)
    ts = date.timestamp() if date else None
    return Document(
        source="telegram-account",
        kind=kind if text.startswith("[") else "message",
        title=f"✈ {str(chat_name)[:60]} · {sender_name[:30]}",
        text=text[:8000],
        sender=sender_name,
        chat=str(chat_name),
        ts=ts,
        metadata={"dialog": str(chat_name)},
    )


async def iter_account_messages(max_per_dialog: int = 200,
                                max_dialogs: int = 200):
    """Async generator: yield Documents for recent messages across dialogs."""
    c = client()
    await c.connect()
    if not await c.is_user_authorized():
        await c.disconnect()
        raise RuntimeError("not logged in — run `dream tg-login` first")
    n = 0
    async for dialog in c.iter_dialogs(limit=max_dialogs):
        chat_name = getattr(dialog.entity, "title", None) or \
            getattr(dialog.entity, "username", None) or "unknown"
        count = 0
        async for msg in c.iter_messages(dialog.entity, limit=max_per_dialog):
            d = message_to_document(msg, default_chat=chat_name)
            if d:
                yield d
                n += 1
                count += 1
                if count >= max_per_dialog or n >= max_dialogs * max_per_dialog:
                    break
        if n >= max_dialogs * max_per_dialog:
            break
    await c.disconnect()


async def sync_account(store, embedder,
                       max_per_dialog: int = 200,
                       max_dialogs: int = 200) -> int:
    """Pull account messages into the store. Returns count."""
    batch, texts = [], []
    total = 0
    async for d in iter_account_messages(max_per_dialog, max_dialogs):
        batch.append(d)
        texts.append(f"{d.title}\n{d.text}")
        if len(batch) >= 100:
            vecs = embedder.embed_many(texts)
            store.add_many(zip(batch, vecs))
            total += len(batch)
            batch, texts = [], []
    if batch:
        vecs = embedder.embed_many(texts)
        store.add_many(zip(batch, vecs))
        total += len(batch)
    return total


# ---------- userbot assistant mode -------------------------------------

async def userbot_loop(store, embedder, watch_chat: str | None = None):
    """Listen for commands sent to 'Saved Messages' (or watch_chat).

    Any message there is treated like the bot bridge: /ask /search /stats
    /remember /export /sync, plain text → saved. Files sent there are
    downloaded and indexed. Optionally mirrors every message in
    watch_chat into memory when /watch is enabled.
    """
    import asyncio
    from . import telegram_bot  # reuse command handling logic pieces
    from .sources import telegram as tg_api

    c = client()
    await c.connect()
    if not await c.is_user_authorized():
        raise RuntimeError("not logged in — run `dream tg-login` first")
    me = await c.get_me()
    saved = await c.get_entity("me")  # Saved Messages
    target = await c.get_entity(watch_chat) if watch_chat else saved
    print(f"userbot listening as @{getattr(me,'username','?')} — "
          f"send commands to {'Saved Messages' if not watch_chat else watch_chat}")

    watch_file = _SESSION_DIR / "tg_watch.json"
    watch_on = False
    if watch_file.exists():
        try:
            watch_on = json.loads(watch_file.read_text()).get("on", False)
        except Exception:
            pass

    async for event in c.iter_messages(target, limit=None):
        msg = event.message
        if not msg:
            continue
        text = (event.raw_text or "").strip()
        # file ingest — download via telethon, index text or store path
        if event.document or event.photo:
            try:
                import time as _t
                dest = await event.download_media(
                    file=str(_SESSION_DIR / "inbox"))
                if not dest:
                    await event.reply("download failed")
                    continue
                p = Path(dest)
                try:
                    body = p.read_text(encoding="utf-8")
                    d = Document(source="telegram-account", kind="file",
                                 title=f"📎 {p.name}", text=body[:8000],
                                 sender="me", chat="telegram-files",
                                 ts=_t.time(), metadata={"path": str(p)})
                    store.add(d, embedder.embed(f"{d.title}\n{body[:2000]}"))
                    await event.reply(f"indexed '{p.name}' ({len(body)} chars) ✓")
                except (UnicodeDecodeError, OSError):
                    d = Document(source="telegram-account", kind="file",
                                 title=f"📎 {p.name}",
                                 text=f"[binary file saved: {p}] size={p.stat().st_size}B",
                                 sender="me", chat="telegram-files",
                                 ts=_t.time(), metadata={"path": str(p)})
                    store.add(d, embedder.embed(d.title))
                    await event.reply(f"saved '{p.name}' (binary — metadata indexed) ✓")
            except Exception as e:
                await event.reply(f"file error: {e}")
            continue

        if not text:
            continue

        # commands — reuse bot handler by faking an update
        fake = {"update_id": 0, "message": {
            "message_id": event.id, "date": int(event.date.timestamp()),
            "chat": {"id": 1, "type": "private"},
            "from": {"first_name": "me"},
            "text": text}}
        # patch handle_update's store/embedder usage via direct call
        reply = telegram_bot.handle_update(fake, store, embedder)
        # /export needs a real chat_id for sendDocument — telethon path:
        if text.startswith("/export"):
            q = text.split(None, 1)[1] if " " in text else ""
            hits = store.hybrid_search(q, embedder.embed(q), 10)
            if hits:
                lines = [f"# Internet's Dream export — {q}", ""]
                for h in hits:
                    doc = store.get(h.doc_id)
                    lines += [f"## {doc['title']}", "", doc.get("text", "")[:4000],
                              "", "---", ""]
                out = _SESSION_DIR / "inbox" / f"export-{int(__import__('time').time())}.md"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text("\n".join(lines))
                await c.send_file(target, str(out), caption=f"{len(hits)} memories")
                reply = f"sent {len(hits)} memories as file ✓"
            else:
                reply = "no matches"
        if reply:
            await event.reply(reply[:4000])

        # mirror mode: save every message in watch_chat
        if watch_on and event.chat_id != saved.id:
            d = message_to_document(event)
            if d:
                store.add(d, embedder.embed(f"{d.title}\n{d.text}"))
