"""Local files adapter — indexes text-readable files in a directory.

Supports .txt .md .markdown .rst .json .csv .log .py .js .ts .html .css
and any file that decodes as UTF-8. Files are chunked (~1800 chars with
small overlap). Binary files are skipped. Path stays in metadata so you
can find "that PDF receipt" later — binary contents are not parsed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from ..store import Document

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
              ".idea", ".vscode", "dist", "build"}
_TEXT_EXT = {".txt", ".md", ".markdown", ".rst", ".json", ".csv", ".log",
             ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".htm", ".css",
             ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh"}
_MAX_FILE = 2 * 1024 * 1024      # 2 MB
_CHUNK = 1800
_OVERLAP = 200


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in _TEXT_EXT:
        return True
    try:
        with open(path, "rb") as f:
            sample = f.read(4096)
        return b"\x00" not in sample
    except OSError:
        return False


def _chunks(text: str):
    start = 0
    while start < len(text):
        yield text[start:start + _CHUNK]
        start += _CHUNK - _OVERLAP


def iter_files(root: str | Path,
               max_files: int = 5000) -> Iterator[Document]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            try:
                if p.stat().st_size > _MAX_FILE or not is_text_file(p):
                    continue
                raw = p.read_bytes()
                text = raw.decode("utf-8", errors="strict")
            except (OSError, UnicodeDecodeError):
                continue
            rel = str(p.relative_to(root))
            for i, chunk in enumerate(_chunks(text)):
                yield Document(
                    source="files",
                    kind="file",
                    title=f"📄 {rel}" + (f" #{i+1}" if i else ""),
                    text=chunk,
                    sender="filesystem",
                    chat=str(root),
                    ts=p.stat().st_mtime,
                    metadata={"path": str(p), "chunk": i, "size": p.stat().st_size},
                )
            n += 1
            if n >= max_files:
                return
