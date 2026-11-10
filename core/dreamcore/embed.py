"""Embedders: deterministic local hashing embedder (default, offline)
plus an optional OpenAI-compatible embeddings endpoint."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

_DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class HashEmbedder:
    """Feature-hashing bag-of-words embedder. Deterministic, dependency-free,
    good enough for hybrid retrieval on a personal corpus."""

    dims = _DIM

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        tokens = _tokens(text)
        if not tokens:
            return vec
        for tok in tokens:
            h = int(hashlib.blake2b(tok.encode(), digest_size=8).hexdigest(), 16)
            idx = h % _DIM
            sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
            vec[idx] += sign
        # sublinear tf + L2 norm
        vec = [math.copysign(math.sqrt(abs(v)), v) for v in vec]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


@dataclass
class EmbedderConfig:
    base_url: str | None = None  # e.g. https://api.openai.com/v1 or Ollama
    api_key: str | None = None
    model: str = "text-embedding-3-small"


class APIEmbedder:
    """OpenAI-compatible /v1/embeddings client (works with OpenAI, Gemini's
    OpenAI-compat endpoint, Ollama, llama.cpp, etc.)."""

    def __init__(self, cfg: EmbedderConfig):
        import httpx
        self._cfg = cfg
        self._client = httpx.Client(timeout=30.0)

    @property
    def dims(self) -> int:
        return 0  # determined at runtime; store checks len() per vector

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        url = self._cfg.base_url.rstrip("/") + "/embeddings"
        headers = {}
        if self._cfg.api_key:
            headers["Authorization"] = f"Bearer {self._cfg.api_key}"
        out = []
        for i in range(0, len(texts), 64):
            batch = texts[i:i + 64]
            r = self._client.post(url, json={
                "model": self._cfg.model, "input": batch,
            }, headers=headers)
            r.raise_for_status()
            data = sorted(r.json()["data"], key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
        return out

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]


def get_embedder(cfg: EmbedderConfig | None = None):
    if cfg and cfg.base_url:
        return APIEmbedder(cfg)
    return HashEmbedder()
