"""Embedding providers for OKF RAG.

The default provider is deterministic and dependency-free so tests and local
fixtures do not need external model services. Runtime deployments can replace
this seam with a provider-specific implementation later.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[\wА-Яа-яЁё-]+", re.UNICODE)


@dataclass(frozen=True)
class EmbeddingProvider:
    model: str
    dimensions: int

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Hashing-vector embedding provider for deterministic tests/local mode."""

    def __init__(self, *, dimensions: int = 64, model: str = "deterministic-hash-v1") -> None:
        super().__init__(model=model, dimensions=max(8, dimensions))

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = _TOKEN_RE.findall(text.casefold()) or [text.casefold()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [round(item / norm, 8) for item in vector]


def build_embedding_provider(*, model: str = "", dimensions: int = 64) -> EmbeddingProvider:
    """Build the configured embedding provider.

    Only the deterministic provider is implemented without optional runtime
    dependencies. Non-empty external model names are accepted as metadata for
    now but still use deterministic vectors until a provider plugin is added.
    """

    return DeterministicEmbeddingProvider(dimensions=dimensions or 64, model=model or "deterministic-hash-v1")
