"""Simple keyword retriever with overlap scoring."""

from __future__ import annotations

from collections import Counter

from erdos_engine.models import RetrievedItem


def _tokenize(text: str) -> list[str]:
    return [t.strip(".,:;()[]{}\n\t").lower() for t in text.split() if t.strip()]


class KeywordRetriever:
    """Term-overlap retriever over in-memory documents."""

    def retrieve(
        self,
        query: str,
        docs: list[tuple[str, str, str, dict]],
        top_k: int,
    ) -> list[RetrievedItem]:
        query_tokens = Counter(_tokenize(query))
        results: list[RetrievedItem] = []
        for item_id, item_type, text, metadata in docs:
            doc_tokens = Counter(_tokenize(text))
            overlap = sum(min(doc_tokens[t], qv) for t, qv in query_tokens.items())
            if overlap <= 0:
                continue
            results.append(
                RetrievedItem(
                    item_id=item_id,
                    item_type=item_type,
                    text=text,
                    score=float(overlap),
                    metadata=metadata,
                )
            )
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
