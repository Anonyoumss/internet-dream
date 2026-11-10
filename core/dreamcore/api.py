"""FastAPI backend — `dreamcore serve`.

Endpoints:
  GET  /health
  GET  /stats
  POST /ingest          {path, source?}  — ingest a chat export file
  POST /ingest-text     {source, title, text, sender?, chat?, ts?}
  GET  /search?q=&limit=
  POST /ask             {question}       — retrieve + generate
  GET  /graph
  GET  /documents/{id}
  GET/PUT /config       — LLM gateway config (api_key write-only-ish)
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .embed import get_embedder
from .ingest import parse_discord_export, parse_whatsapp_export
from .llm import LLMConfig, LLMGateway
from .store import Document, Store

DEFAULT_DB = Path.home() / ".internet-dream" / "memory.sqlite3"

class IngestIn(BaseModel):
    path: str
    chat_name: str | None = None


class IngestText(BaseModel):
    source: str = "manual"
    title: str
    text: str
    sender: str | None = None
    chat: str | None = None
    ts: float | None = None


class AskIn(BaseModel):
    question: str


class SyncIn(BaseModel):
    source: str
    options: dict | None = None


class ConfigIn(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    embed_base_url: str | None = None
    embed_api_key: str | None = None
    embed_model: str | None = None




def create_app(db_path: str | os.PathLike | None = None,
               passphrase: str | None = None) -> FastAPI:
    db = Path(db_path) if db_path else DEFAULT_DB
    store = Store(db, passphrase=passphrase)
    embedder = get_embedder()
    app = FastAPI(title="Internet's Dream — dreamcore", version="0.1.0")
    app.state.store = store
    app.state.embedder = embedder

    def _embed_texts(texts: list[str]):
        return embedder.embed_many(texts)

    @app.get("/health")
    def health():
        return {"ok": True, "docs": store.count()}

    @app.get("/stats")
    def stats():
        return store.stats()

    @app.post("/ingest")
    def ingest(body: IngestIn):
        p = Path(body.path)
        if not p.exists():
            raise HTTPException(404, f"file not found: {p}")
        name = p.name.lower()
        if name.endswith(".txt") or "_chat" in name:
            docs = parse_whatsapp_export(p, chat_name=body.chat_name)
        elif name.endswith(".json"):
            docs = parse_discord_export(p)
        else:
            raise HTTPException(400, "unsupported export format (.txt or .json)")
        texts = [f"{d.title}\n{d.text}" for d in docs]
        vecs = _embed_texts(texts)
        store.add_many(zip(docs, vecs))
        return {"ingested": len(docs)}

    @app.post("/ingest-text")
    def ingest_text(body: IngestText):
        doc = Document(
            source=body.source, kind="note", title=body.title, text=body.text,
            sender=body.sender, chat=body.chat, ts=body.ts,
        )
        vec = embedder.embed(f"{doc.title}\n{doc.text}")
        return {"id": store.add(doc, vec)}

    @app.get("/search")
    def search(q: str, limit: int = 20):
        vec = embedder.embed(q)
        return [h.__dict__ for h in store.hybrid_search(q, vec, limit)]

    @app.post("/ask")
    def ask(body: AskIn):
        hits = store.hybrid_search(body.question, embedder.embed(body.question), 8)
        if not hits:
            return {"answer": "I don't have anything indexed about that yet.",
                    "sources": []}
        context = "\n\n".join(
            f"[{h.title} · {h.sender or 'unknown'} · {h.source}]\n{h.snippet}"
            for h in hits
        )
        try:
            gw = LLMGateway()
            answer = gw.chat([
                {"role": "system", "content":
                 "You are the memory core of 'Internet's Dream', a private "
                 "personal second brain. Answer using ONLY the provided "
                 "memories. Cite sources by title. If the memories don't "
                 "contain the answer, say so."},
                {"role": "user", "content":
                 f"Memories:\n{context}\n\nQuestion: {body.question}"},
            ])
        except Exception as e:  # no API key / offline → degrade gracefully
            answer = ("(LLM gateway not configured — showing raw matches)\n\n"
                      + "\n".join(f"• {h.title}: {h.snippet}" for h in hits[:5]))
            return {"answer": answer, "sources": [h.__dict__ for h in hits],
                    "llm_error": str(e)}
        return {"answer": answer, "sources": [h.__dict__ for h in hits]}

    @app.get("/sources")
    def sources():
        from .sources.sync import list_sources
        return list_sources()

    @app.post("/sync")
    def sync(body: SyncIn):
        from .embed import EmbedderConfig, get_embedder
        from .llm import LLMConfig
        from .sources.sync import sync_source
        cfg = LLMConfig.load()
        emb = get_embedder(EmbedderConfig(
            base_url=cfg.embed_base_url, api_key=cfg.embed_api_key,
            model=cfg.embed_model) if cfg.embed_base_url else None)
        try:
            n = sync_source(store, emb, body.source, body.options)
        except KeyError as e:
            raise HTTPException(400, str(e))
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        return {"source": body.source, "synced": n}

    @app.get("/graph")
    def graph():
        return store.graph()

    @app.get("/documents/{doc_id}")
    def document(doc_id: str):
        doc = store.get(doc_id)
        if not doc:
            raise HTTPException(404, "not found")
        return doc

    @app.get("/config")
    def get_config():
        cfg = LLMConfig.load()
        cfg.api_key = "***" if cfg.api_key else None
        if cfg.embed_api_key:
            cfg.embed_api_key = "***"
        return cfg.__dict__

    @app.put("/config")
    def put_config(body: ConfigIn):
        cfg = LLMConfig.load()
        for k, v in body.dict(exclude_none=True).items():
            if k == "api_key" and v == "***":
                continue
            if k == "embed_api_key" and v == "***":
                continue
            setattr(cfg, k, v)
        cfg.save()
        return {"ok": True}

    return app
