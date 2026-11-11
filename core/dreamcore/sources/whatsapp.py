"""WhatsApp source — scans a folder for chat exports (_chat.txt).

Point it at your Downloads/Documents (or a dedicated exports folder);
every WhatsApp 'Export chat' .txt found is parsed into messages.
Re-running is cheap: documents are keyed by content hash.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..ingest.whatsapp import parse_whatsapp_export
from ..store import Document

_EXPORT_NAMES = ("_chat.txt", "chat.txt")


def iter_exports(root: str | Path,
                 max_files: int = 200) -> Iterator[Document]:
    root = Path(root).expanduser()
    if not root.is_dir():
        return
    found = 0
    for p in sorted(root.rglob("*.txt")):
        if found >= max_files:
            break
        name = p.name.lower()
        if not any(k in name for k in _EXPORT_NAMES):
            continue
        # cheap WhatsApp marker check before full parse
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        if not any(m in head for m in ("Messages and calls are",
                                       "missed voice call",
                                       "created group")):
            continue
        yield from parse_whatsapp_export(p)
        found += 1
