"""Telegram adapter — Bot API.

Two modes:
  * `dream sync telegram` — one-shot dump of recent getUpdates into the
    store (read).
  * `dream telegram-bot` — long-running bridge (dreamcore.telegram_bot):
    /ask, /search, /stats, /export <query>, /remember, and auto-ingest of
    documents/photos sent to the bot (read + write + file copy).

Token resolution order: DREAM_TELEGRAM_TOKEN env →
~/.internet-dream/config.json "telegram_bot_token".
Create a bot via @BotFather, then `dream config --telegram-token 123:abc`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

from ..store import Document

_API = "https://api.telegram.org"
_CONFIG = Path.home() / ".internet-dream" / "config.json"


def bot_token() -> str | None:
    tok = os.environ.get("DREAM_TELEGRAM_TOKEN")
    if tok:
        return tok
    if _CONFIG.exists():
        try:
            return json.loads(_CONFIG.read_text()).get("telegram_bot_token")
        except Exception:
            pass
    return None


def _call(method: str, **params):
    import httpx
    tok = bot_token()
    if not tok:
        raise RuntimeError("no telegram bot token — set DREAM_TELEGRAM_TOKEN "
                           "or `dream config --telegram-token`")
    r = httpx.post(f"{_API}/bot{tok}/{method}", json=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"telegram {method}: {data}")
    return data["result"]


def parse_update(u: dict) -> Document | None:
    """Pure parser — testable without network."""
    msg = u.get("message") or u.get("edited_message") or {}
    if not msg:
        return None
    chat = msg.get("chat") or {}
    sender = msg.get("from") or {}
    chat_name = chat.get("title") or " ".join(
        x for x in [sender.get("first_name"), sender.get("last_name")] if x
    ) or chat.get("username") or "unknown"
    sender_name = " ".join(
        x for x in [sender.get("first_name"), sender.get("last_name")] if x
    ) or sender.get("username") or "unknown"

    ts = msg.get("date")
    kind = "message"
    text = ""
    if msg.get("text"):
        kind = "text"
        text = msg["text"]
    elif msg.get("document"):
        kind = "document"
        doc = msg["document"]
        text = f"[file: {doc.get('file_name','?')} {doc.get('file_size','?')}B]"
    elif msg.get("photo"):
        kind = "photo"
        sizes = msg["photo"]
        best = sizes[-1] if sizes else {}
        text = f"[photo {best.get('width','?')}x{best.get('height','?')}]"
    elif msg.get("voice"):
        kind = "voice"
        text = "[voice message]"
    elif msg.get("video"):
        kind = "video"
        text = f"[video: {msg['video'].get('file_name','?')}]"
    else:
        return None

    if not text:
        return None
    return Document(
        source="telegram",
        kind=kind,
        title=f"✈ {chat_name[:60]} · {sender_name[:30]}",
        text=text,
        sender=sender_name,
        chat=chat_name,
        ts=float(ts) if ts else None,
        metadata={"update_id": u.get("update_id"), "chat_id": chat.get("id")},
    )


def get_updates(offset: int | None = None, timeout: int = 0,
                limit: int = 100) -> list[dict]:
    params = {"limit": limit, "timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    return _call("getUpdates", **params)


def download_file(file_id: str, dest_dir: str | Path) -> Path:
    """Download a Telegram file (documents/photos) to dest_dir."""
    import httpx
    info = _call("getFile", file_id=file_id)
    fpath = info["file_path"]
    tok = bot_token()
    dest = Path(dest_dir) / Path(fpath).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET",
                      f"{_API}/file/bot{tok}/{fpath}", timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    return dest


def send_document(chat_id, file_path: str | Path, caption: str = ""):
    import httpx
    tok = bot_token()
    p = Path(file_path)
    with open(p, "rb") as f:
        r = httpx.post(
            f"{_API}/bot{tok}/sendDocument",
            data={"chat_id": chat_id, "caption": caption[:1000]},
            files={"document": (p.name, f)},
            timeout=120)
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text: str):
    return _call("sendMessage", chat_id=chat_id, text=text[:4000])


def iter_updates(max_results: int = 1000) -> Iterator[Document]:
    """Dump recent updates as Documents (one-shot sync source)."""
    offset = None
    n = 0
    while n < max_results:
        updates = get_updates(offset=offset, limit=min(100, max_results - n))
        if not updates:
            break
        for u in updates:
            offset = u["update_id"] + 1
            doc = parse_update(u)
            if doc:
                yield doc
                n += 1
                if n >= max_results:
                    return
