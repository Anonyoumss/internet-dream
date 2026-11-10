"""LLM gateway — provider-agnostic chat completions.

Providers:
  openai-compatible : POST {base}/chat/completions  (OpenAI, Gemini OpenAI-compat,
                       Ollama http://localhost:11434/v1, llama.cpp, etc.)
  anthropic         : POST https://api.anthropic.com/v1/messages

Config file: ~/.internet-dream/config.json
  {
    "provider": "openai-compatible",
    "base_url": "https://api.openai.com/v1",
    "api_key": "...",
    "model": "gpt-4o-mini",
    "embed": {"base_url": ..., "api_key": ..., "model": ...}
  }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import httpx

_CONFIG_PATH = Path.home() / ".internet-dream" / "config.json"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class LLMConfig:
    provider: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    embed_base_url: str | None = None
    embed_api_key: str | None = None
    embed_model: str = "text-embedding-3-small"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "LLMConfig":
        p = Path(path) if path else _CONFIG_PATH
        env_key = os.environ.get("DREAM_LLM_API_KEY")
        if not p.exists():
            return cls(api_key=env_key)
        data = json.loads(p.read_text())
        embed = data.get("embed") or {}
        return cls(
            provider=data.get("provider", "openai-compatible"),
            base_url=data.get("base_url", "https://api.openai.com/v1"),
            api_key=env_key or data.get("api_key"),
            model=data.get("model", "gpt-4o-mini"),
            embed_base_url=embed.get("base_url") or data.get("embed_base_url"),
            embed_api_key=embed.get("api_key") or data.get("embed_api_key"),
            embed_model=embed.get("model", "text-embedding-3-small"),
        )

    def save(self, path: str | Path | None = None) -> None:
        p = Path(path) if path else _CONFIG_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "provider": self.provider,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model": self.model,
            "embed": {
                "base_url": self.embed_base_url,
                "api_key": self.embed_api_key,
                "model": self.embed_model,
            },
        }, indent=2))
        os.chmod(p, 0o600)


class LLMGateway:
    def __init__(self, cfg: LLMConfig | None = None, client: httpx.Client | None = None):
        self.cfg = cfg or LLMConfig.load()
        self._client = client or httpx.Client(timeout=60.0)

    # -- chat ------------------------------------------------------------

    def chat(self, messages: list[dict], *, model: str | None = None,
             temperature: float = 0.3, max_tokens: int = 1024) -> str:
        if self.cfg.provider == "anthropic":
            return self._chat_anthropic(messages, model, temperature, max_tokens)
        return self._chat_openai_compat(messages, model, temperature, max_tokens)

    def _chat_openai_compat(self, messages, model, temperature, max_tokens) -> str:
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        r = self._client.post(url, json={
            "model": model or self.cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _chat_anthropic(self, messages, model, temperature, max_tokens) -> str:
        system = ""
        convo = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                convo.append({
                    "role": m["role"],
                    "content": [{"type": "text", "text": m["content"]}],
                })
        headers = {
            "x-api-key": self.cfg.api_key or "",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        r = self._client.post(ANTHROPIC_URL, json={
            "model": model or self.cfg.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": convo,
        }, headers=headers)
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))

    # -- embeddings --------------------------------------------------------

    def embed_config(self):
        from .embed import EmbedderConfig
        return EmbedderConfig(
            base_url=self.cfg.embed_base_url,
            api_key=self.cfg.embed_api_key,
            model=self.cfg.embed_model,
        )
