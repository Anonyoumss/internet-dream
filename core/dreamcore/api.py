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

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
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


class ChatIn(BaseModel):
    message: str
    history: list[dict] | None = None


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


class ResearchIn(BaseModel):
    question: str
    use_web: bool = True


class SpeakIn(BaseModel):
    text: str


class VisionIn(BaseModel):
    image_base64: str
    mime: str = "image/png"
    question: str = "Describe this image."


class JobIn(BaseModel):
    prompt: str
    interval_seconds: int = 3600
    enabled: bool = True


class ForgetIn(BaseModel):
    query: str
    limit: int = 5




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

    # -- rate limiting (simple in-memory, per client IP) ----------------
    from collections import defaultdict, deque
    _hits: dict[str, deque] = defaultdict(deque)

    def _rate_limit(request: Request, limit: int = 30, window: int = 60):
        ip = request.client.host if request.client else "?"
        now = __import__("time").time()
        dq = _hits[ip]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= limit:
            raise HTTPException(429, "rate limit — slow down")
        dq.append(now)

    @app.post("/chat")
    def chat(body: ChatIn, request: Request):
        """Agent chat — LLM with tools over the memory store."""
        from .agent import run_agent
        _rate_limit(request, limit=40, window=60)
        history = (body.history or [])[-20:]
        messages = history + [{"role": "user", "content": body.message}]
        try:
            return run_agent(store, embedder, messages)
        except Exception as e:
            raise HTTPException(502, f"agent failed: {e}")

    @app.post("/research")
    def research(body: ResearchIn):
        """Deep research — plan → memory+web search → cited report."""
        from .research import deep_research
        try:
            return deep_research(store, embedder, body.question,
                                 use_web=body.use_web)
        except Exception as e:
            raise HTTPException(502, f"research failed: {e}")

    @app.get("/export")
    def export(q: str = "", limit: int = 500):
        """Export matching memories as a Markdown file."""
        from fastapi.responses import Response
        if q:
            hits = store.hybrid_search(q, embedder.embed(q), limit)
            docs = [{"title": h.title, "sender": h.sender, "source": h.source,
                     "chat": h.chat, "ts": h.ts, "snippet": h.snippet}
                    for h in hits]
        else:
            docs = [d for d in store.iter_documents()][:limit]
        lines = ["# Internet's Dream — memory export", ""]
        for d in docs:
            ts = ""
            if d.get("ts"):
                import datetime
                ts = datetime.datetime.fromtimestamp(
                    d["ts"]).strftime("%Y-%m-%d %H:%M")
            lines += [
                f"## {d.get('title','?')}",
                f"*{d.get('sender') or '?'} · {d.get('source','?')}"
                + (f" · {ts}" if ts else "") + "*",
                "", d.get("text") or d.get("snippet") or "", "---", ""]
        return Response(
            "\n".join(lines), media_type="text/markdown",
            headers={"Content-Disposition":
                     "attachment; filename=internet-dream-export.md"})

    @app.delete("/documents/{doc_id}")
    def forget_doc(doc_id: str):
        """Forget a single memory (GDPR-friendly)."""
        if not store.delete(doc_id):
            raise HTTPException(404, "not found")
        return {"deleted": doc_id}

    @app.post("/forget")
    def forget_matching(body: ForgetIn):
        """Forget memories matching a query (search → delete top N)."""
        hits = store.hybrid_search(body.query, embedder.embed(body.query),
                                   body.limit)
        ids = []
        for h in hits:
            if store.delete(h.doc_id):
                ids.append(h.doc_id)
        return {"forgotten": len(ids), "ids": ids}

    @app.post("/transcribe")
    async def transcribe(file: UploadFile):
        """Speech-to-text via faster-whisper (optional dependency)."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise HTTPException(
                501, "install faster-whisper: pip install faster-whisper")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as t:
            t.write(await file.read())
            tmp = t.name
        try:
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(tmp)
            return {"text": " ".join(s.text for s in segments).strip()}
        finally:
            import os
            os.unlink(tmp)

    @app.post("/speak")
    async def speak(body: SpeakIn):
        """Text-to-speech via edge-tts (optional dependency)."""
        try:
            import io
            import edge_tts
            buf = io.BytesIO()
            communicate = edge_tts.Communicate(body.text,
                                                "en-US-AriaNeural")
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            from fastapi.responses import Response
            return Response(buf.getvalue(), media_type="audio/mpeg")
        except ImportError:
            raise HTTPException(501, "install edge-tts: pip install edge-tts")

    @app.post("/vision")
    def vision(body: VisionIn):
        """Image understanding via the configured OpenAI-compatible model
        (works with Gemini — it accepts image_url parts)."""
        import base64
        cfg = LLMConfig.load()
        if cfg.provider != "openai-compatible":
            raise HTTPException(400, "vision needs an openai-compatible provider")
        import httpx
        url = cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        try:
            r = httpx.post(url, headers=headers, timeout=120, json={
                "model": cfg.model,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": body.question},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{body.mime};base64,{body.image_base64}"}},
                ]}],
                "max_tokens": 1024,
            })
            r.raise_for_status()
            return {"answer": r.json()["choices"][0]["message"]["content"]}
        except Exception as e:
            raise HTTPException(502, f"vision failed: {e}")

    # -- scheduled agent jobs --------------------------------------------

    @app.get("/jobs")
    def jobs_list():
        from . import jobs as _jobs
        return _jobs.list_jobs()

    @app.post("/jobs")
    def jobs_add(body: JobIn):
        from . import jobs as _jobs
        return _jobs.add_job(body.prompt, body.interval_seconds, body.enabled)

    @app.delete("/jobs/{job_id}")
    def jobs_delete(job_id: str):
        from . import jobs as _jobs
        if not _jobs.remove_job(job_id):
            raise HTTPException(404, "job not found")
        return {"deleted": job_id}

    @app.on_event("startup")
    async def _start_scheduler():
        from . import jobs as _jobs
        import asyncio
        asyncio.create_task(
            _jobs.scheduler_loop(store, embedder, log=print))

    @app.post("/ingest-upload")
    async def ingest_upload(file: UploadFile):
        """Upload a chat export (.txt WhatsApp / .json Discord) — saved to
        ~/.internet-dream/inbox/ then parsed."""
        inbox = Path.home() / ".internet-dream" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        dest = inbox / (file.filename or "upload.bin")
        dest.write_bytes(await file.read())
        name = dest.name.lower()
        if name.endswith(".txt") or "_chat" in name:
            docs = parse_whatsapp_export(dest)
        elif name.endswith(".json"):
            docs = parse_discord_export(dest)
        else:
            raise HTTPException(400, "unsupported export format (.txt or .json)")
        texts = [f"{d.title}\n{d.text}" for d in docs]
        vecs = _embed_texts(texts)
        store.add_many(zip(docs, vecs))
        return {"ingested": len(docs), "saved": str(dest)}

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

    # -- Google OAuth (backend-managed; one consent for all clients) ------

    @app.get("/auth/google/start")
    def google_start(request: Request):
        from . import oauth
        try:
            url = oauth.auth_url(
                request.url.hostname or "127.0.0.1",
                request.url.port or 80)
        except Exception as e:
            raise HTTPException(400, str(e))
        return RedirectResponse(url)

    @app.get("/auth/google/callback")
    def google_callback(request: Request, code: str = "", error: str = ""):
        from urllib.parse import quote
        from . import oauth
        if error:
            return RedirectResponse(f"/#/sources?google_error={quote(error)}")
        try:
            oauth.handle_callback(
                code,
                request.url.hostname or "127.0.0.1",
                request.url.port or 80)
        except Exception as e:
            return RedirectResponse(f"/#/sources?google_error={quote(str(e))}")
        return RedirectResponse("/#/sources?google=connected")

    @app.get("/auth/status")
    def auth_status():
        from .sources import google_auth, telegram
        return {
            "google": {
                "client_configured": google_auth.available(),
                "token_present": google_auth.TOKEN_FILE.exists(),
                "scopes": google_auth.SCOPES,
            },
            "telegram": {"bot_token": bool(telegram.bot_token())},
        }

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
