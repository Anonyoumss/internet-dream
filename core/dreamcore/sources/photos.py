"""Google Photos adapter — indexes photo metadata via the Photos Picker API.

Google deprecated the old photoslibrary API; Picker sessions are the
supported path. We index metadata only (filename, description, creation
time, dimensions, mime type) — image bytes are never downloaded, which is
deliberate: memories about *what/when/where* without hoarding pixels.
"""

from __future__ import annotations

import time
from typing import Iterator

from ..store import Document
from . import google_auth

_PICKER = "https://photospicker.googleapis.com/v1"


def parse_media_item(item: dict) -> Document | None:
    """Pure parser — testable without network."""
    media_file = item.get("mediaFile") or {}
    filename = media_file.get("filename") or "photo"
    desc = media_file.get("description") or ""
    mime = media_file.get("mimeType", "")
    meta = item.get("mediaMetadata") or {}
    width, height = meta.get("width", 0), meta.get("height", 0)
    creation = meta.get("creationTime")
    ts = None
    if creation:
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(
                str(creation).replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    text = f"Photo: {filename}"
    if desc:
        text += f"\nDescription: {desc}"
    text += f"\nType: {mime} {width}x{height}"
    return Document(
        source="photos",
        kind="photo",
        title=f"🖼 {filename[:80]}",
        text=text,
        sender="google-photos",
        chat="google-photos",
        ts=ts,
        metadata={
            "media_item_id": item.get("id", ""),
            "mime_type": mime,
            "width": width, "height": height,
        },
    )


def _request(creds, method: str, url: str, **kwargs):
    import google.auth.transport.requests as tr
    authed = tr.AuthorizedSession(creds)
    return authed.request(method, url, timeout=60, **kwargs)


def iter_media_items(max_items: int = 10000) -> Iterator[Document]:
    """Create a Picker session, poll until ready, then page mediaItems."""
    creds = google_auth.credentials()

    # 1) create session
    r = _request(creds, "POST", f"{_PICKER}/sessions",
                 json={"pickerUri": _PICKER + "/pickerUri-placeholder"})
    # Picker API expects an empty body create; real flow:
    # POST /v1/sessions with {"pickerUri": "..."}? — actual API: POST sessions
    # returns {id, pickerUri, expirationTime, mediaItemsSet}. The create
    # call takes no body in current docs; retry without json if 400.
    if r.status_code >= 400:
        r = _request(creds, "POST", f"{_PICKER}/sessions")
    r.raise_for_status()
    session = r.json()
    session_id = session["id"]

    # 2) poll until mediaItemsSet
    for _ in range(30):
        r = _request(creds, "GET", f"{_PICKER}/sessions/{session_id}")
        r.raise_for_status()
        s = r.json()
        if s.get("mediaItemsSet"):
            break
        time.sleep(2)
    else:
        raise RuntimeError("Picker session timed out waiting for media items")

    # 3) page through items
    page_token = None
    fetched = 0
    while fetched < max_items:
        params = {"pageSize": 100}
        if page_token:
            params["pageToken"] = page_token
        r = _request(creds, "GET", f"{_PICKER}/mediaItems",
                     params=params)
        r.raise_for_status()
        data = r.json()
        for item in data.get("mediaItems", []):
            doc = parse_media_item(item)
            if doc:
                yield doc
            fetched += 1
            if fetched >= max_items:
                break
        page_token = data.get("nextPageToken")
        if not page_token:
            break
