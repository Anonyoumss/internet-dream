"""Sync orchestration — pull documents from a named source into the store.

Each source yields Document objects lazily; we embed and store in batches
so memory stays flat on huge exports.
"""

from __future__ import annotations

from typing import Callable, Iterator

from ..store import Document, Store
from . import (browser, calendar, discord_api, drive, files, gmail, photos,
               telegram, whatsapp, youtube)

BATCH = 100


def _gmail(opts) -> Iterator[Document]:
    yield from gmail.iter_messages(
        query=opts.get("query", "in:inbox OR in:sent"),
        max_results=int(opts.get("max_results", 500)))


def _calendar(opts) -> Iterator[Document]:
    yield from calendar.iter_events(
        calendar_id=opts.get("calendar_id", "primary"),
        past_days=int(opts.get("past_days", 365)),
        future_days=int(opts.get("future_days", 365)),
        max_results=int(opts.get("max_results", 2500)))


def _photos(opts) -> Iterator[Document]:
    yield from photos.iter_media_items(
        max_items=int(opts.get("max_items", 10000)))


def _browser(opts) -> Iterator[Document]:
    yield from browser.iter_history(which=opts.get("which"),
                                    max_results=int(opts.get("max_results", 20000)))


def _files(opts) -> Iterator[Document]:
    yield from files.iter_files(opts.get("path", "."),
                                max_files=int(opts.get("max_files", 5000)))


def _drive(opts) -> Iterator[Document]:
    yield from drive.iter_files(
        max_results=int(opts.get("max_results", 5000)),
        include_text=bool(opts.get("include_text", True)),
        query=opts.get("query", "trashed=false"))


def _youtube(opts) -> Iterator[Document]:
    yield from youtube.iter_youtube(opts)


def _discord(opts) -> Iterator[Document]:
    yield from discord_api.iter_discord(opts)


def _whatsapp(opts) -> Iterator[Document]:
    yield from whatsapp.iter_exports(
        opts.get("path", "~/Downloads"),
        max_files=int(opts.get("max_files", 200)))


def _telegram(opts) -> Iterator[Document]:
    yield from telegram.iter_updates(
        max_results=int(opts.get("max_results", 1000)))


SOURCES: dict[str, dict] = {
    "gmail": {
        "label": "Gmail",
        "description": "Email messages (readonly scope)",
        "requires_google_auth": True,
        "factory": _gmail,
        "options": {"query": "in:inbox OR in:sent", "max_results": 500},
    },
    "calendar": {
        "label": "Google Calendar",
        "description": "Events ±365 days (readonly scope)",
        "requires_google_auth": True,
        "factory": _calendar,
        "options": {"calendar_id": "primary", "past_days": 365,
                    "future_days": 365, "max_results": 2500},
    },
    "photos": {
        "label": "Google Photos",
        "description": "Photo metadata via Picker API (no image download)",
        "requires_google_auth": True,
        "factory": _photos,
        "options": {"max_items": 10000},
    },
    "browser": {
        "label": "Browser history",
        "description": "Chrome/Chromium + Firefox visited pages",
        "requires_google_auth": False,
        "factory": _browser,
        "options": {"which": None, "max_results": 20000},
    },
    "files": {
        "label": "Local files",
        "description": "Text-readable files in a directory (chunked)",
        "requires_google_auth": False,
        "factory": _files,
        "options": {"path": ".", "max_files": 5000},
    },
    "drive": {
        "label": "Google Drive",
        "description": "File metadata + text content (readonly scope)",
        "requires_google_auth": True,
        "factory": _drive,
        "options": {"max_results": 5000, "include_text": True,
                    "query": "trashed=false"},
    },
    "youtube": {
        "label": "YouTube history",
        "description": "Watch/search history from Google Takeout export",
        "requires_google_auth": False,
        "factory": _youtube,
        "options": {"path": "~/Downloads/.../watch-history.html"},
    },
    "discord": {
        "label": "Discord",
        "description": "Your servers' messages via user token (read-only)",
        "requires_google_auth": False,
        "factory": _discord,
        "options": {"max_per_channel": 500, "include_dms": False,
                    "guild": None},
    },
    "whatsapp": {
        "label": "WhatsApp",
        "description": "Chat exports (_chat.txt) found in a folder — "
                       "export from WhatsApp → attach .txt → drop here",
        "requires_google_auth": False,
        "factory": _whatsapp,
        "options": {"path": "~/Downloads", "max_files": 200},
    },
    "telegram": {
        "label": "Telegram",
        "description": "Recent bot-visible messages (needs bot token)",
        "requires_google_auth": False,
        "factory": _telegram,
        "options": {"max_results": 1000},
    },
}


def list_sources() -> list[dict]:
    return [{
        "id": k,
        "label": v["label"],
        "description": v["description"],
        "requires_google_auth": v["requires_google_auth"],
        "options": v["options"],
    } for k, v in SOURCES.items()]


def sync_source(store: Store, embedder, name: str,
                opts: dict | None = None,
                progress: Callable[[int], None] | None = None) -> int:
    """Ingest one source into the store. Returns document count."""
    if name not in SOURCES:
        raise KeyError(f"unknown source '{name}'. Available: {', '.join(SOURCES)}")
    spec = SOURCES[name]
    options = {**spec["options"], **(opts or {})}

    total = 0
    batch: list[tuple[Document, list[float]]] = []
    texts: list[str] = []

    def flush():
        nonlocal batch, texts, total
        if not batch:
            return
        vecs = embedder.embed_many(texts)
        store.add_many(zip(batch, vecs))
        total += len(batch)
        if progress:
            progress(total)
        batch, texts = [], []

    for doc in spec["factory"](options):
        batch.append(doc)
        texts.append(f"{doc.title}\n{doc.text}")
        if len(batch) >= BATCH:
            flush()
    flush()
    return total
