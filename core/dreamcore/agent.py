"""Agent — tool-calling chat loop over the memory store.

The LLM can call tools to search memories, sync sources, save notes,
and inspect stats — so the chat can actually *do* things, not just
answer. OpenAI-compatible providers with function calling are used
when available; otherwise we degrade to a single-shot answer.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import httpx

from .embed import get_embedder
from .llm import LLMConfig, LLMGateway
from .store import Document, Store

MAX_STEPS = 6

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search the user's indexed memories (chats, "
                           "email, browser history, files) by keyword/meaning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 8},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Save a note/fact into long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["title", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sync_source",
            "description": "Pull fresh data from a connected source "
                           "(gmail, calendar, drive, photos, browser, "
                           "files, youtube, telegram, discord).",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "options": {"type": "object"},
                },
                "required": ["source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stats",
            "description": "Memory store statistics: total docs, counts "
                           "per source.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_sources",
            "description": "List available data sources and their options.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

SYSTEM = """You are Internet's Dream — a personal AI agent with access to the
user's private, encrypted memory of their digital life (chats, email,
browser history, files, calendar).

Rules:
- Use search_memory to find relevant memories before answering questions
  about the user's life, preferences, or history.
- Use remember to save anything the user asks you to keep, or important
  facts they share.
- Use sync_source when the user asks to refresh/import data, or when
  memories seem stale.
- Use get_stats / list_sources to answer questions about what's indexed.
- Be concise and cite memory titles when you use them.
- Never invent memories — if search finds nothing, say so."""


def _tool_search_memory(store: Store, embedder, args: dict) -> str:
    q = args.get("query", "")
    limit = int(args.get("limit", 8))
    hits = store.hybrid_search(q, embedder.embed(q), limit)
    if not hits:
        return "No matching memories found."
    return "\n\n".join(
        f"[{h.title} · {h.sender or '?'} · {h.source}]\n{h.snippet}"
        for h in hits)


def _tool_remember(store: Store, embedder, args: dict) -> str:
    doc = Document(source="agent", kind="note",
                   title=args.get("title", "Note"),
                   text=args.get("text", ""))
    vec = embedder.embed(f"{doc.title}\n{doc.text}")
    doc_id = store.add(doc, vec)
    return f"Saved to memory (id {doc_id})."


def _tool_sync_source(store: Store, embedder, args: dict) -> str:
    from .sources.sync import sync_source
    name = args.get("source", "")
    try:
        n = sync_source(store, embedder, name, args.get("options") or {})
        return f"Synced {n} documents from {name}."
    except Exception as e:
        return f"Sync failed: {e}"


def _tool_get_stats(store: Store, embedder, args: dict) -> str:
    return json.dumps(store.stats())


def _tool_list_sources(store: Store, embedder, args: dict) -> str:
    from .sources.sync import list_sources
    return json.dumps(list_sources())


_DISPATCH: dict[str, Callable] = {
    "search_memory": _tool_search_memory,
    "remember": _tool_remember,
    "sync_source": _tool_sync_source,
    "get_stats": _tool_get_stats,
    "list_sources": _tool_list_sources,
}


def run_agent(store: Store, embedder, messages: list[dict],
              cfg: LLMConfig | None = None) -> dict:
    """Run the agent loop. Returns {answer, steps, sources?}."""
    cfg = cfg or LLMConfig.load()
    gw = LLMGateway(cfg)
    convo = [{"role": "system", "content": SYSTEM}, *messages]
    steps: list[dict] = []
    sources: list[dict] = []

    for _ in range(MAX_STEPS):
        msg = _chat_with_tools(gw, convo)
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            answer = msg.get("content") or ""
            return {"answer": answer, "steps": steps}

        convo.append(msg)
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = _DISPATCH.get(name)
            step = {"tool": name, "args": args}
            if handler:
                try:
                    result = handler(store, embedder, args)
                except Exception as e:
                    result = f"error: {e}"
            else:
                result = f"unknown tool {name}"
            step["result"] = result[:300]
            steps.append(step)
            if name == "search_memory":
                try:
                    q = args.get("query", "")
                    hits = store.hybrid_search(q, embedder.embed(q), 8)
                    sources = [h.__dict__ for h in hits]
                except Exception:
                    pass
            convo.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })

    # hit step cap — ask for a final plain answer
    convo.append({"role": "user", "content":
                  "Please give your final answer now based on what you found."})
    try:
        answer = gw.chat(convo)
    except Exception as e:
        answer = f"(agent stopped: {e})"
    return {"answer": answer, "steps": steps, "sources": sources}


def _chat_with_tools(gw: LLMGateway, messages: list[dict]) -> dict:
    """One chat completion returning the raw assistant message.

    Only openai-compatible providers support tool calls here; for
    anthropic we simulate by appending a hint and doing plain chat.
    """
    cfg = gw.cfg
    if cfg.provider != "openai-compatible":
        # graceful degradation: plain chat, tools described in prompt
        text = gw.chat(messages + [{
            "role": "user",
            "content": "(Tools unavailable for this provider — answer "
                       "directly from the conversation.)",
        }])
        return {"role": "assistant", "content": text}

    url = cfg.base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    try:
        r = gw._client.post(url, json={
            "model": cfg.model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.3,
            "max_tokens": 1024,
        }, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]
    except (httpx.HTTPError, KeyError, IndexError):
        # provider may not support tools — fall back to plain chat
        text = gw.chat(messages)
        return {"role": "assistant", "content": text}
