"""Google Drive adapter — indexes file metadata via Drive API v3.

One Document per file: name, mime type, modified time, size, owner,
web link. For text-like mime types (text/*, JSON, CSV) the content is
also downloaded (capped) and indexed — Google-native Docs/Sheets are
recorded by metadata only (export can be added later).
"""

from __future__ import annotations

from typing import Iterator

from ..store import Document
from . import google_auth

_TEXT_MIMES = {
    "text/plain", "text/markdown", "text/csv", "application/json",
    "application/xml", "text/html",
}
_MAX_TEXT = 200_000


def parse_file_meta(f: dict) -> Document:
    """Pure parser — testable without network."""
    name = f.get("name") or "unnamed"
    mime = f.get("mimeType") or ""
    owners = ", ".join(o.get("displayName", "") for o in f.get("owners", [])[:3])
    size = f.get("size")
    text = (f"File: {name}\nType: {mime}\n"
            f"Modified: {f.get('modifiedTime','')}\n"
            f"Size: {size or '?'} bytes\nOwner: {owners or '?'}\n"
            f"Link: {f.get('webViewLink','')}")
    return Document(
        source="drive",
        kind="drive-file",
        title=f"🗂 {name[:80]}",
        text=text,
        sender=owners or "google-drive",
        chat="google-drive",
        ts=None,
        metadata={
            "file_id": f.get("id", ""), "mime_type": mime,
            "size": size, "web_view_link": f.get("webViewLink", ""),
        },
    )


def _ts(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def iter_files(max_results: int = 5000,
               include_text: bool = True,
               query: str = "trashed=false") -> Iterator[Document]:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io

    creds = google_auth.credentials()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    page_token = None
    fetched = 0
    fields = ("nextPageToken, files(id,name,mimeType,modifiedTime,size,"
              "webViewLink,owners(emailAddress,displayName))")
    while fetched < max_results:
        resp = service.files().list(
            q=query, pageSize=min(200, max_results - fetched),
            fields=fields, pageToken=page_token,
            orderBy="modifiedTime desc").execute()
        for f in resp.get("files", []):
            doc = parse_file_meta(f)
            doc.ts = _ts(f.get("modifiedTime"))
            mime = f.get("mimeType", "")
            if include_text and mime in _TEXT_MIMES and f.get("size", 10**9) < _MAX_TEXT:
                try:
                    req = service.files().get_media(fileId=f["id"])
                    buf = io.BytesIO()
                    dl = MediaIoBaseDownload(buf, req)
                    done = False
                    while not done:
                        _, done = dl.next_chunk()
                    content = buf.getvalue().decode("utf-8", errors="replace")
                    if content.strip():
                        # index content as a companion document
                        yield Document(
                            source="drive", kind="file-content",
                            title=f"🗂 {f.get('name','')[:80]} (content)",
                            text=content[:_MAX_TEXT],
                            sender=doc.sender, chat="google-drive",
                            ts=doc.ts,
                            metadata={"file_id": f["id"], "parent": doc.title},
                        )
                except Exception:
                    pass  # unreadable file — metadata doc still yielded
            yield doc
            fetched += 1
            if fetched >= max_results:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
