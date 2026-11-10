"""Parser for DiscordChatExporter (Tyrrrz/DiscordChatExporter) JSON output.

Supports the standard export shape:
  { "guild": {...}, "channel": {...}, "messages": [ {id, timestamp,
    content, author:{name,...}, attachments:[{url,...}] } ] }
and a bare top-level list of messages.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..store import Document


def _ts(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) / 1000.0 if value > 1e12 else float(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_discord_export(path: str | Path) -> list[Document]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        channel_name, messages = path.stem, data
    else:
        channel = data.get("channel") or {}
        channel_name = channel.get("name") or data.get("channelName") or path.stem
        messages = data.get("messages") or []

    docs: list[Document] = []
    for msg in messages:
        content = (msg.get("content") or "").strip()
        attachments = msg.get("attachments") or []
        att_txt = " ".join(
            f"[attachment: {a.get('fileName') or a.get('url','')}]"
            for a in attachments
        )
        text = "\n".join(t for t in (content, att_txt) if t).strip()
        if not text:
            continue
        author = (msg.get("author") or {}).get("name") or msg.get("authorName") or "unknown"
        docs.append(Document(
            source="discord",
            kind="message",
            title=f"#{channel_name} · {author}",
            text=text,
            sender=author,
            chat=f"#{channel_name}",
            ts=_ts(msg.get("timestamp")),
            metadata={"message_id": str(msg.get("id", "")), "export": str(path)},
        ))
    return docs
