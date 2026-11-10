"""Browser history adapter — indexes Chrome/Chromium and Firefox history.

Reads the browser's places database read-only (copied to a temp file so
we never touch a locked/live DB). One Document per visited page.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator

from ..store import Document

_CHROME_CANDIDATES = [
    Path.home() / ".config/google-chrome/Default/History",
    Path.home() / ".config/chromium/Default/History",
    Path.home() / "Library/Application Support/Google/Chrome/Default/History",
]
_FIREFOX_CANDIDATES = [
    Path.home() / ".mozilla/firefox",
]


def _chrome_history(path: Path) -> Iterator[tuple]:
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        shutil.copy(path, tmp_path)
        conn = sqlite3.connect(str(tmp_path))
        rows = conn.execute(
            """SELECT url, title, last_visit_time, visit_count
               FROM urls ORDER BY last_visit_time DESC LIMIT 20000""")
        for url, title, lvt, vc in rows:
            # chrome time = microseconds since 1601-01-01
            ts = (lvt / 1_000_000) - 11_644_473_600 if lvt else None
            yield url, title or "", ts, vc
        conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)


def _firefox_dbs() -> list[Path]:
    out = []
    for base in _FIREFOX_CANDIDATES:
        if base.is_dir():
            out.extend(base.glob("*/places.sqlite"))
    return out


def _firefox_history(path: Path) -> Iterator[tuple]:
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        shutil.copy(path, tmp_path)
        conn = sqlite3.connect(str(tmp_path))
        rows = conn.execute(
            """SELECT p.url, p.title, MAX(v.visit_date)/1000000, COUNT(*)
               FROM moz_places p JOIN moz_historyvisits v
                 ON v.place_id = p.id
               GROUP BY p.id ORDER BY 3 DESC LIMIT 20000""")
        for url, title, ts, vc in rows:
            yield url, title or "", ts, vc
        conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)


def discover() -> list[dict]:
    """List detected browser history sources."""
    found = []
    for p in _CHROME_CANDIDATES:
        if p.exists():
            found.append({"id": f"chrome:{p.parent.name}", "path": str(p),
                          "browser": "chrome", "profile": p.parent.name})
    for p in _firefox_dbs():
        found.append({"id": f"firefox:{p.parent.name}", "path": str(p),
                      "browser": "firefox", "profile": p.parent.name})
    return found


def parse_visit(url: str, title: str, ts: float | None,
                visits: int, browser: str) -> Document | None:
    if not url or url.startswith(("chrome://", "about:", "file://")):
        return None
    label = title or url
    return Document(
        source="browser",
        kind="visit",
        title=f"🌐 {label[:80]}",
        text=f"Visited: {url}\nTitle: {label}\nVisits: {visits}",
        sender=browser,
        chat=f"{browser}-history",
        ts=ts,
        metadata={"url": url, "visits": visits},
    )


def iter_history(which: str | None = None,
                 max_results: int = 20000) -> Iterator[Document]:
    """Yield Documents for all (or one named) detected browser histories."""
    sources = discover()
    if which:
        sources = [s for s in sources if which in s["id"]]
    for s in sources:
        path = Path(s["path"])
        rows = (_chrome_history(path) if s["browser"] == "chrome"
                else _firefox_history(path))
        n = 0
        for url, title, ts, vc in rows:
            doc = parse_visit(url, title, ts, vc, s["browser"])
            if doc:
                yield doc
                n += 1
            if n >= max_results:
                break
