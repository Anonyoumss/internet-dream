"""Local vector store: SQLite + AES-256-GCM payloads + FTS5 index.

Layout:
  documents(id, source, kind, ts, sender, chat, title, payload BLOB,
            vector BLOB, dims, created)
  search_index — FTS5 over (title, sender, chat, source, ts_text)

The `payload` column is AES-256-GCM ciphertext; the FTS index holds only
the metadata needed to find documents (documented limitation: metadata
is plaintext, content is not).
"""

from __future__ import annotations

import json
import sqlite3
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .crypto import get_or_create_key

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    ts REAL,
    sender TEXT,
    chat TEXT,
    title TEXT,
    payload BLOB NOT NULL,
    vector BLOB,
    dims INTEGER,
    created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_docs_chat ON documents(chat);
CREATE INDEX IF NOT EXISTS idx_docs_ts ON documents(ts);
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    doc_id UNINDEXED, title, sender, chat, source, ts_text,
    tokenize = 'porter unicode61'
);
"""


def _locked(fn):
    def wrapper(self, *a, **k):
        with self._lock:
            return fn(self, *a, **k)
    wrapper.__name__ = fn.__name__
    return wrapper


@dataclass
class Hit:
    doc_id: str
    score: float
    title: str
    sender: str | None
    chat: str | None
    source: str
    ts: float | None
    snippet: str = ""


@dataclass
class Document:
    source: str
    kind: str
    title: str
    text: str
    sender: str | None = None
    chat: str | None = None
    ts: float | None = None
    metadata: dict = field(default_factory=dict)


def _pack_vector(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack_vector(buf: bytes) -> list[float]:
    n = len(buf) // 4
    return list(struct.unpack(f"<{n}f", buf))


class Store:
    def __init__(self, path: str | Path, passphrase: str | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._aes = get_or_create_key(passphrase)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- write -----------------------------------------------------------

    @_locked
    def add(self, doc: Document, vector: list[float] | None = None) -> str:
        doc_id = uuid.uuid4().hex
        payload = json.dumps(
            {"text": doc.text, "metadata": doc.metadata}, ensure_ascii=False
        ).encode("utf-8")
        nonce = __import__("os").urandom(12)
        ct = self._aes.encrypt(nonce, payload, doc_id.encode())
        blob = nonce + ct

        self._conn.execute(
            """INSERT INTO documents
               (id, source, kind, ts, sender, chat, title, payload,
                vector, dims, created)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                doc_id, doc.source, doc.kind, doc.ts, doc.sender, doc.chat,
                doc.title, blob,
                _pack_vector(vector) if vector else None,
                len(vector) if vector else None,
                time.time(),
            ),
        )
        ts_text = time.strftime("%Y-%m-%d", time.localtime(doc.ts)) if doc.ts else ""
        self._conn.execute(
            """INSERT INTO search_index
               (doc_id, title, sender, chat, source, ts_text)
               VALUES (?,?,?,?,?,?)""",
            (doc_id, doc.title, doc.sender or "", doc.chat or "",
             doc.source, ts_text),
        )
        self._conn.commit()
        return doc_id

    @_locked
    def add_many(self, docs: Iterable[tuple[Document, list[float] | None]]):
        for doc, vec in docs:
            self.add(doc, vec)

    # -- read ------------------------------------------------------------

    def _decrypt(self, row: sqlite3.Row) -> dict:
        blob = row["payload"]
        nonce, ct = blob[:12], blob[12:]
        pt = self._aes.decrypt(nonce, ct, row["id"].encode())
        return json.loads(pt.decode("utf-8"))

    @_locked
    def get(self, doc_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM documents WHERE id=?", (doc_id,)
        ).fetchone()
        if not row:
            return None
        data = self._decrypt(row)
        return {
            "id": row["id"], "source": row["source"], "kind": row["kind"],
            "ts": row["ts"], "sender": row["sender"], "chat": row["chat"],
            "title": row["title"], **data,
        }

    def iter_documents(self):
        for row in self._conn.execute("SELECT * FROM documents"):
            yield self.get(row["id"])

    @_locked
    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]

    @_locked
    def stats(self) -> dict:
        rows = self._conn.execute(
            """SELECT source, COUNT(*) c FROM documents GROUP BY source"""
        ).fetchall()
        kinds = self._conn.execute(
            """SELECT kind, COUNT(*) c FROM documents GROUP BY kind"""
        ).fetchall()
        return {
            "total": self.count(),
            "by_source": {r["source"]: r["c"] for r in rows},
            "by_kind": {r["kind"]: r["c"] for r in kinds},
        }

    # -- search ----------------------------------------------------------

    @_locked
    def fts_search(self, query: str, limit: int = 20) -> list[Hit]:
        match = " ".join(f'"{t}"' for t in query.split() if t)
        if not match:
            return []
        try:
            rows = self._conn.execute(
                """SELECT doc_id, bm25(search_index) score FROM search_index
                   WHERE search_index MATCH ? ORDER BY score LIMIT ?""",
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        hits = []
        for r in rows:
            doc = self.get(r["doc_id"])
            if not doc:
                continue
            hits.append(Hit(
                doc_id=doc["id"], score=-r["score"], title=doc["title"],
                sender=doc["sender"], chat=doc["chat"], source=doc["source"],
                ts=doc["ts"], snippet=(doc.get("text") or "")[:160],
            ))
        return hits

    @_locked
    def vector_search(self, query_vec: list[float], limit: int = 20) -> list[Hit]:
        rows = self._conn.execute(
            "SELECT * FROM documents WHERE vector IS NOT NULL"
        ).fetchall()
        qn = sum(x * x for x in query_vec) ** 0.5 or 1.0
        scored = []
        for row in rows:
            vec = _unpack_vector(row["vector"])
            if len(vec) != len(query_vec):
                continue
            dn = sum(x * x for x in vec) ** 0.5 or 1.0
            sim = sum(a * b for a, b in zip(query_vec, vec)) / (qn * dn)
            scored.append((sim, row))
        scored.sort(key=lambda t: t[0], reverse=True)
        hits = []
        for sim, row in scored[:limit]:
            doc = self.get(row["id"])
            hits.append(Hit(
                doc_id=doc["id"], score=sim, title=doc["title"],
                sender=doc["sender"], chat=doc["chat"], source=doc["source"],
                ts=doc["ts"], snippet=(doc.get("text") or "")[:160],
            ))
        return hits

    @_locked
    def hybrid_search(self, query: str, query_vec: list[float] | None,
                      limit: int = 20) -> list[Hit]:
        """Reciprocal-rank fusion of FTS5 + vector results."""
        fts = self.fts_search(query, limit * 2)
        vec = self.vector_search(query_vec, limit * 2) if query_vec else []
        scores: dict[str, float] = {}
        docs: dict[str, Hit] = {}
        for rank, h in enumerate(fts):
            scores[h.doc_id] = scores.get(h.doc_id, 0) + 1.0 / (60 + rank)
            docs[h.doc_id] = h
        for rank, h in enumerate(vec):
            scores[h.doc_id] = scores.get(h.doc_id, 0) + 1.0 / (60 + rank)
            docs.setdefault(h.doc_id, h)
        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        out = []
        for doc_id, score in ordered:
            h = docs[doc_id]
            h.score = score
            out.append(h)
        return out

    # -- graph -----------------------------------------------------------

    @_locked
    def graph(self, limit: int = 200) -> dict:
        """Nodes = chats/senders; edges = shared docs (for dashboard viz)."""
        rows = self._conn.execute(
            """SELECT chat, sender, source, COUNT(*) c FROM documents
               WHERE chat IS NOT NULL GROUP BY chat, sender
               ORDER BY c DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        nodes, edges = [], []
        seen = set()
        for i, r in enumerate(rows):
            chat = r["chat"] or "unknown"
            sender = r["sender"] or "unknown"
            for label in (chat, sender):
                if label not in seen:
                    seen.add(label)
                    nodes.append({"id": label, "group": 1 if label == chat else 2})
            edges.append({
                "source": chat, "target": sender, "value": r["c"],
            })
        return {"nodes": nodes[: limit * 2], "edges": edges}
