"""Deep research — plan → search → read → synthesize pipeline.

Grok DeepSearch pattern: decompose the question, gather evidence from
memory AND the live web, then write a cited report.
"""

from __future__ import annotations

import json
import re

from .agent import _tool_read_url, _tool_web_search
from .llm import LLMGateway
from .store import Store


def _parse_json_array(text: str) -> list[str]:
    # extract the first JSON array anywhere in the output
    m = re.search(r"\[[\s\S]*?\]", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list) and data:
                return [str(x) for x in data][:5]
        except json.JSONDecodeError:
            pass
    # fallback: bullet-ish lines
    out = []
    for ln in text.splitlines():
        ln = ln.strip().lstrip("-*• ").strip('"')
        if ln and not ln.startswith(("[", "]", "{")):
            out.append(ln)
    return out[:5]


def deep_research(store: Store, embedder, question: str,
                  use_web: bool = True, max_sources: int = 8) -> dict:
    """Run the full pipeline. Returns {report, plan, sources, steps}."""
    gw = LLMGateway()
    embedder_fn = embedder.embed

    # 1 — PLAN sub-queries (memory + optionally web)
    plan_prompt = (
        "Break this research question into 2-5 focused sub-queries. "
        "Some should target the user's personal memory (chats, files, "
        "email), some the live web if needed. Reply ONLY as a JSON array "
        "of strings.\n\nQuestion: " + question)
    try:
        plan_raw = gw.chat([
            {"role": "system", "content": "You are a research planner. Output only JSON."},
            {"role": "user", "content": plan_prompt},
        ], max_tokens=400)
    except Exception:
        plan_raw = '["' + question + '"]'
    queries = _parse_json_array(plan_raw) or [question]

    steps = [{"stage": "plan", "queries": queries}]
    evidence: list[dict] = []

    # 2 — MEMORY evidence
    for q in queries:
        try:
            hits = store.hybrid_search(q, embedder_fn(q), 4)
            for h in hits:
                evidence.append({
                    "kind": "memory", "title": h.title,
                    "source": h.source, "text": h.snippet[:1200],
                })
        except Exception:
            pass

    # 3 — WEB evidence (optional)
    if use_web:
        seen_urls = set()
        for q in queries[:3]:
            try:
                results_text = _tool_web_search(store, embedder, {"query": q})
            except Exception:
                continue
            urls = re.findall(r"https?://[^\s)\]]+", results_text)
            for url in urls[:2]:
                if url in seen_urls or "duckduckgo" in url:
                    continue
                seen_urls.add(url)
                try:
                    body = _tool_read_url(store, embedder, {"url": url})
                except Exception:
                    continue
                evidence.append({
                    "kind": "web", "title": url, "url": url,
                    "text": body[:2500],
                })
                if len(evidence) >= max_sources + 8:
                    break
            if len(evidence) >= max_sources + 8:
                break
        steps.append({"stage": "web", "sources": len(seen_urls)})

    steps.append({"stage": "evidence", "count": len(evidence)})

    # 4 — SYNTHESIZE report
    ctx_parts = []
    for e in evidence[:max_sources]:
        tag = f"MEMORY [{e.get('source','?')}]" if e["kind"] == "memory" else f"WEB {e.get('url','')}"
        ctx_parts.append(f"### {e['title']} ({tag})\n{e['text']}")
    context = "\n\n".join(ctx_parts) or "(no evidence found)"

    try:
        report = gw.chat([
            {"role": "system", "content":
             "You are a research analyst. Write a thorough, well-structured "
             "report answering the question. Cite memory sources by title "
             "and web sources by URL. Clearly separate 'From your memories' "
             "and 'From the web'. Say what's uncertain."},
            {"role": "user", "content":
             f"Question: {question}\n\nEvidence:\n{context}"},
        ], max_tokens=2048)
    except Exception as e:
        report = f"(report generation failed: {e})\n\nEvidence gathered:\n{context[:2000]}"

    return {
        "question": question,
        "report": report,
        "plan": queries,
        "sources": evidence[:max_sources],
        "steps": steps,
    }
