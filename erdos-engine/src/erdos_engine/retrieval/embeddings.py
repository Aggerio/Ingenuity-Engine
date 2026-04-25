"""Embedding retrieval interface placeholder for future vector backends."""

from __future__ import annotations

from erdos_engine.models import RetrievedItem


class EmbeddingsRetriever:
    """No-op embeddings retriever for v0 local harness."""

    def available(self) -> bool:
        return False

    def retrieve(self, query: str, tags: list[str], top_k: int) -> list[RetrievedItem]:
        _ = (query, tags, top_k)
        return []
