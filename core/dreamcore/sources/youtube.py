"""YouTube history adapter — parses Google Takeout exports.

YouTube watch history is not exposed by the Data API, so the real path is
Google Takeout → "YouTube and YouTube Music" → watch-history.html.

Also accepts the per-month JSON variant some Takeout versions emit.
One Document per watched video.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Iterator

from ..store import Document

# Takeout HTML: <a href="https://www.youtube.com/watch?v=...">Title</a>
# inside content-cell blocks; channel + timestamp nearby.
_WATCH = re.compile(
    r'<a[^>]+href="(https://www\.youtube\.com/watch\?[^"]+)"[^>]*>(.*?)</a>',
    re.S)
_CHANNEL = re.compile(r'<a[^>]+href="https://www\.youtube\.com/channel/[^"]*"[^>]*>(.*?)</a>', re.S)
_TIME = re.compile(r'(\d{1,2}\s+\w+\s+\d{4},?\s+\d{1,2}:\d{2}[^<]*)')
_TAG = re.compile(r'<[^>]+>')


def _clean(html: str) -> str:
    return unescape(_TAG.sub("", html)).strip()


def _ts_from(text: str) -> float | None:
    for fmt in ("%d %B %Y, %H:%M:%S", "%d %B %Y, %H:%M",
                "%B %d, %Y, %I:%M:%S %p", "%d %b %Y, %H:%M"):
        try:
            return datetime.strptime(text.strip(), fmt).timestamp()
        except ValueError:
            continue
    return None


def parse_watch_history_html(path: str | Path) -> list[Document]:
    """Parse watch-history.html (or search-history.html) from Takeout."""
    path = Path(path)
    html = path.read_text(encoding="utf-8", errors="replace")
    docs: list[Document] = []
    # split into content cells so channel/time stay associated
    cells = re.split(r'<div class="content-cell">', html)
    for cell in cells[1:]:
        m = _WATCH.search(cell)
        if not m:
            continue
        url, title_html = m.group(1), m.group(2)
        title = _clean(title_html) or url
        ch = _CHANNEL.search(cell)
        channel = _clean(ch.group(1)) if ch else "unknown"
        tm = _TIME.search(cell)
        ts = _ts_from(tm.group(1)) if tm else None
        docs.append(Document(
            source="youtube",
            kind="watch",
            title=f"▶ {title[:80]}",
            text=f"Watched: {title}\nURL: {url}\nChannel: {channel}",
            sender=channel,
            chat="youtube-history",
            ts=ts,
            metadata={"url": url, "export": str(path)},
        ))
    return docs


def parse_takeout_json(path: str | Path) -> list[Document]:
    """Parse Takeout JSON activity exports (array of activity records)."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("item", [])
    docs = []
    for it in items:
        title = it.get("title") or ""
        if not title:
            continue
        ts = None
        try:
            ts = datetime.fromisoformat(
                str(it.get("time", "")).replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError):
            pass
        docs.append(Document(
            source="youtube", kind="activity",
            title=f"▶ {title[:80]}",
            text=f"{title}\n{it.get('titleUrl','')}\n{it.get('header','')}",
            sender="youtube-takeout", chat="youtube-history",
            ts=ts, metadata={"export": str(path)},
        ))
    return docs


def parse_any(path: str | Path) -> list[Document]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        return parse_takeout_json(p)
    return parse_watch_history_html(p)


def iter_youtube(opts: dict) -> Iterator[Document]:
    """sync factory: opts['path'] required (or 'paths' list)."""
    paths = opts.get("paths") or ([opts["path"]] if opts.get("path") else [])
    if not paths:
        raise ValueError("youtube source needs --opt path=<watch-history.html> "
                         "(from Google Takeout)")
    for p in paths:
        for d in parse_any(p):
            yield d
