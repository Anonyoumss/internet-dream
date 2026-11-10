"""Sync orchestration — pull documents from a named source into the store.

Each source yields Document objects lazily; we embed and store in batches
so memory stays flat on huge exports.
"""

from __future__ import annotations

from typing import Callable, Iterator

from ..store import Document, Store
from . import browser, calendar, files, gmail, photos

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
