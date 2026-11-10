"""Parser for WhatsApp "Export chat" _chat.txt files.

Format (locale variants covered):
    [12/31/23, 10:15:32 PM] Alice: message text
    [31/12/23, 22:15:32] Bob: message
    continuation lines belong to the previous message.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path

from ..store import Document

# [date, time] sender: body   — sender may contain most chars except ':'
_LINE = re.compile(
    r"^\[(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),?\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?)\]\s+"
    r"(?P<sender>[^:]{1,80}?):\s?(?P<body>.*)$",
    re.IGNORECASE,
)

_SYSTEM = re.compile(
    r"(added|removed|left|changed (the )?(group )?name|changed this group's|"
    r"created (the )?group|pinned|unpinned|this message was deleted|"
    r"joined using this group.s invite link)",
    re.IGNORECASE,
)

_DATE_FORMATS = (
    "%d/%m/%y %I:%M:%S %p", "%d/%m/%Y %I:%M:%S %p",
    "%m/%d/%y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S %p",
    "%d/%m/%y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
    "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
    "%d/%m/%y %I:%M %p", "%m/%d/%y %I:%M %p",
    "%d/%m/%y %H:%M", "%m/%d/%y %H:%M",
)


def _parse_ts(date_s: str, time_s: str) -> float | None:
    s = f"{date_s.strip()} {time_s.strip()}"
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            continue
    return None


def iter_whatsapp(path: str | Path, chat_name: str | None = None):
    """Yield Document objects for each message in a WhatsApp export."""
    path = Path(path)
    chat_name = chat_name or path.parent.name or path.stem
    current = None
    buf: list[str] = []

    def flush():
        nonlocal current, buf
        if current is None:
            return None
        body = "\n".join(buf).strip()
        buf = []
        if not body or _SYSTEM.search(body) and len(body) < 120:
            # keep system lines out of the searchable corpus
            if _SYSTEM.search(body):
                return
        sender, ts, first = current
        yield_doc = Document(
            source="whatsapp",
            kind="message",
            title=f"{chat_name} · {sender}",
            text=body,
            sender=sender,
            chat=chat_name,
            ts=ts,
            metadata={"export": str(path), "first_line": first},
        )
        return yield_doc

    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = _LINE.match(line)
            if m:
                doc = flush()
                if doc is not None:
                    yield doc
                sender = m.group("sender").strip()
                ts = _parse_ts(m.group("date"), m.group("time"))
                buf = [m.group("body")]
                current = (sender, ts, line)
            elif current is not None:
                buf.append(line)
        doc = flush()
        if doc is not None:
            yield doc


def parse_whatsapp_export(path: str | Path, chat_name: str | None = None) -> list[Document]:
    return list(iter_whatsapp(path, chat_name))
