"""`dream` CLI.

  dream init [--passphrase X]
  dream ingest <file> [--chat-name NAME]
  dream ingest-text --title T --text "..." [--source S] [--sender U] [--chat C]
  dream search <query> [--limit N]
  dream ask <question>
  dream stats
  dream graph
  dream config [--provider P --base-url U --api-key K --model M]
  dream serve [--host 127.0.0.1] [--port 8765] [--db PATH]
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from .api import DEFAULT_DB, create_app
from .embed import get_embedder
from .ingest import parse_discord_export, parse_whatsapp_export
from .llm import LLMConfig, LLMGateway
from .store import Document, Store


def _store(args) -> Store:
    return Store(getattr(args, "db", None) or DEFAULT_DB,
                 passphrase=getattr(args, "passphrase", None))


def cmd_init(args):
    pw = args.passphrase or getpass.getpass("Passphrase (empty = random key): ")
    store = _store(args)
    print(f"Initialized store at {store.path} "
          f"({store.count()} docs). Key: {'passphrase-derived' if pw else 'random, stored in ~/.internet-dream/key'}")
    store.close()


def cmd_ingest(args):
    p = Path(args.file)
    name = p.name.lower()
    if name.endswith(".txt") or "_chat" in name:
        docs = parse_whatsapp_export(p, chat_name=args.chat_name)
    elif name.endswith(".json"):
        docs = parse_discord_export(p)
    else:
        sys.exit("unsupported format — use a WhatsApp _chat.txt or DiscordChatExporter .json")
    store = _store(args)
    emb = get_embedder()
    texts = [f"{d.title}\n{d.text}" for d in docs]
    vecs = emb.embed_many(texts)
    store.add_many(zip(docs, vecs))
    print(f"ingested {len(docs)} documents from {p.name}")
    store.close()


def cmd_ingest_text(args):
    store = _store(args)
    doc = Document(source=args.source, kind="note", title=args.title,
                   text=args.text, sender=args.sender, chat=args.chat)
    vec = get_embedder().embed(f"{doc.title}\n{doc.text}")
    print(store.add(doc, vec))
    store.close()


def _search(store, args):
    emb = get_embedder()
    return store.hybrid_search(args.query if hasattr(args, "query") else args.question,
                               emb.embed(args.query if hasattr(args, "query") else args.question),
                               getattr(args, "limit", 20))


def cmd_search(args):
    store = _store(args)
    for h in _search(store, args):
        print(f"[{h.score:.3f}] {h.title} — {h.sender or '?'} ({h.source})")
        print(f"    {h.snippet[:140]}")
    store.close()


def cmd_ask(args):
    store = _store(args)
    hits = _search(store, args)
    if not hits:
        print("No matching memories found.")
        store.close()
        return
    context = "\n\n".join(f"[{h.title} · {h.sender or '?'}]\n{h.snippet}" for h in hits[:8])
    try:
        gw = LLMGateway()
        ans = gw.chat([
            {"role": "system", "content":
             "You are the memory core of 'Internet's Dream', a private personal "
             "second brain. Answer using ONLY the memories provided. Cite "
             "sources by title."},
            {"role": "user", "content": f"Memories:\n{context}\n\nQuestion: {args.question}"},
        ])
        print(ans)
    except Exception as e:
        print(f"(LLM gateway unavailable: {e}) — top matches:")
        for h in hits[:5]:
            print(f"• {h.title}: {h.snippet[:120]}")
    store.close()


def cmd_stats(args):
    store = _store(args)
    print(json.dumps(store.stats(), indent=2))
    store.close()


def cmd_graph(args):
    store = _store(args)
    print(json.dumps(store.graph(), indent=2))
    store.close()


def cmd_config(args):
    cfg = LLMConfig.load()
    if args.provider: cfg.provider = args.provider
    if args.base_url: cfg.base_url = args.base_url
    if args.api_key: cfg.api_key = args.api_key
    if args.model: cfg.model = args.model
    if args.embed_base_url: cfg.embed_base_url = args.embed_base_url
    if args.embed_model: cfg.embed_model = args.embed_model
    if args.telegram_token: cfg.telegram_bot_token = args.telegram_token
    cfg.save()
    safe = cfg.__dict__.copy()
    safe["api_key"] = "***" if cfg.api_key else None
    safe["embed_api_key"] = "***" if cfg.embed_api_key else None
    safe["telegram_bot_token"] = "***" if cfg.telegram_bot_token else None
    print(json.dumps(safe, indent=2))


def cmd_telegram_bot(args):
    from .telegram_bot import run
    run(poll_timeout=args.poll_timeout)


def cmd_sources(args):
    from .sources.sync import list_sources
    for s in list_sources():
        flag = " [google auth]" if s["requires_google_auth"] else ""
        print(f"{s['id']:10} {s['label']}{flag}\n           {s['description']}")
        opts = ", ".join(f"{k}={v!r}" for k, v in s["options"].items())
        print(f"           options: {opts}")


def cmd_auth(args):
    from .sources import google_auth
    creds = google_auth.credentials()
    print(f"Authorized. Token stored at {google_auth.token_path()} "
          f"(scopes: {', '.join(s.rsplit('/',1)[-1] for s in google_auth.SCOPES)})")


def cmd_sync(args):
    from .sources.sync import sync_source
    from .embed import EmbedderConfig, get_embedder
    store = _store(args)
    cfg = LLMConfig.load()
    emb = get_embedder(EmbedderConfig(
        base_url=cfg.embed_base_url, api_key=cfg.embed_api_key,
        model=cfg.embed_model) if cfg.embed_base_url else None)
    opts = {}
    for kv in args.opt or []:
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                v = int(v)
            except ValueError:
                try:
                    v = float(v)
                except ValueError:
                    pass
            opts[k] = v
    n = sync_source(store, emb, args.source, opts,
                    progress=lambda c: print(f"\r  {c} docs…", end="", flush=True))
    print(f"\n{args.source}: synced {n} documents")
    store.close()


def cmd_serve(args):
    import uvicorn
    uvicorn.run(create_app(db_path=args.db, passphrase=args.passphrase),
                host=args.host, port=args.port)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dream", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="path to memory.sqlite3")
    ap.add_argument("--passphrase", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.set_defaults(fn=cmd_init)

    p = sub.add_parser("ingest"); p.add_argument("file")
    p.add_argument("--chat-name"); p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("ingest-text")
    p.add_argument("--title", required=True); p.add_argument("--text", required=True)
    p.add_argument("--source", default="manual")
    p.add_argument("--sender"); p.add_argument("--chat")
    p.set_defaults(fn=cmd_ingest_text)

    p = sub.add_parser("search"); p.add_argument("query")
    p.add_argument("--limit", type=int, default=20); p.set_defaults(fn=cmd_search)

    p = sub.add_parser("ask"); p.add_argument("question")
    p.add_argument("--limit", type=int, default=8); p.set_defaults(fn=cmd_ask)

    p = sub.add_parser("stats"); p.set_defaults(fn=cmd_stats)
    p = sub.add_parser("graph"); p.set_defaults(fn=cmd_graph)

    p = sub.add_parser("config")
    p.add_argument("--provider"); p.add_argument("--base-url")
    p.add_argument("--api-key"); p.add_argument("--model")
    p.add_argument("--embed-base-url"); p.add_argument("--embed-model")
    p.add_argument("--telegram-token", help="Telegram bot token from @BotFather")
    p.set_defaults(fn=cmd_config)

    p = sub.add_parser("telegram-bot", help="run the Telegram bot bridge")
    p.add_argument("--poll-timeout", type=int, default=30)
    p.set_defaults(fn=cmd_telegram_bot)

    p = sub.add_parser("sources"); p.set_defaults(fn=cmd_sources)

    p = sub.add_parser("auth"); p.set_defaults(fn=cmd_auth)

    p = sub.add_parser("sync")
    from .sources.sync import SOURCES as _SRC
    p.add_argument("source", choices=sorted(_SRC))
    p.add_argument("--opt", action="append", help="key=value option, repeatable")
    p.set_defaults(fn=cmd_sync)

    p = sub.add_parser("serve")
    p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=8765)
    p.set_defaults(fn=cmd_serve)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
