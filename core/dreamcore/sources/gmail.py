"""Gmail adapter — indexes message metadata + body text via Gmail API.

Yields one Document per message. Uses gmail.readonly scope; body text is
extracted from text/plain parts (HTML stripped as fallback). Attachments
are recorded by name only — contents are never downloaded.
"""

from __future__ import annotations

import base64
import re
import time
from typing import Iterator

from ..store import Document
from . import google_auth

_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")


def _b64url(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
        "utf-8", errors="replace")


def _headers(payload: dict) -> dict:
    return {h["name"].lower(): h["value"]
            for h in (payload.get("headers") or [])}


def _walk_parts(payload: dict):
    """Yield (mime_type, body_data) for every part."""
    if payload.get("body", {}).get("data"):
        yield payload.get("mimeType", ""), payload["body"]["data"]
    for part in payload.get("parts") or []:
        yield from _walk_parts(part)


def extract_body(payload: dict, limit: int = 8000) -> str:
    plain, html = [], []
    for mime, data in _walk_parts(payload):
        try:
            text = _b64url(data)
        except Exception:
            continue
        if mime == "text/plain":
            plain.append(text)
        elif mime == "text/html":
            html.append(text)
    body = "\n".join(plain) if plain else "\n".join(html)
    if not plain and html:
        body = _TAG.sub(" ", body)
        body = _WS.sub(" ", body)
    return body[:limit]


def parse_message(msg: dict) -> Document | None:
    """Pure parser — testable without network."""
    payload = msg.get("payload") or {}
    headers = _headers(payload)
    subject = headers.get("subject") or "(no subject)"
    sender = headers.get("from") or "unknown"
    snippet = msg.get("snippet") or ""
    body = extract_body(payload)
    text = body or snippet
    if not text.strip():
        return None
    ts = None
    try:
        ts = int(msg.get("internalDate", 0)) / 1000.0
    except (TypeError, ValueError):
        pass
    return Document(
        source="gmail",
        kind="email",
        title=f"✉ {subject[:80]}",
        text=text,
        sender=sender,
        chat="gmail",
        ts=ts,
        metadata={
            "message_id": msg.get("id", ""),
            "thread_id": msg.get("threadId", ""),
            "to": headers.get("to", ""),
            "date": headers.get("date", ""),
        },
    )


def iter_messages(query: str = "in:inbox OR in:sent",
                  max_results: int = 500,
                  page_size: int = 100) -> Iterator[Document]:
    """Fetch messages matching `query` (Gmail search syntax)."""
    from googleapiclient.discovery import build

    creds = google_auth.credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    page_token = None
    fetched = 0
    while fetched < max_results:
        resp = service.users().messages().list(
            userId="me", q=query,
            maxResults=min(page_size, max_results - fetched),
            pageToken=page_token).execute()
        for stub in resp.get("messages", []):
            full = service.users().messages().get(
                userId="me", id=stub["id"], format="full").execute()
            doc = parse_message(full)
            if doc:
                yield doc
            fetched += 1
            if fetched >= max_results:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
