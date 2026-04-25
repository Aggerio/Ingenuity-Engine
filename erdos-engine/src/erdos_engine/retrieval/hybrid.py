"""Hybrid retriever combining keyword and optional embedding results."""

from __future__ import annotations

from erdos_engine.models import RetrievedItem
from erdos_engine.retrieval.embeddings import EmbeddingsRetriever
from erdos_engine.retrieval.keyword import KeywordRetriever
from erdos_engine.store.failure_store import FailureStore
from erdos_engine.store.lemma_store import LemmaStore


class HybridRetriever:
    """Combine retrieval from lemmas, proof moves, and failure memory."""

    def __init__(self, lemma_store: LemmaStore, failure_store: FailureStore) -> None:
        self.lemma_store = lemma_store
        self.failure_store = failure_store
        self.keyword = KeywordRetriever()
        self.embeddings = EmbeddingsRetriever()

    def retrieve(self, query: str, tags: list[str], top_k: int, problem_id: str) -> list[RetrievedItem]:
        docs: list[tuple[str, str, str, dict]] = []
        for lemma in self.lemma_store.load_lemmas():
            if tags and not set(tags).intersection(set(lemma.domain_tags)):
                continue
            docs.append(
                (
                    lemma.id,
                    "lemma",
                    f"{lemma.title}. {lemma.statement}. {lemma.conclusion}",
                    {"tags": lemma.domain_tags, "source": lemma.source},
                )
            )
        for move in self.lemma_store.load_proof_moves():
            docs.append(
                (
                    move.id,
                    "proof_move",
                    f"{move.claim}. {move.rationale}. {move.expected_effect}",
                    {"move_type": move.move_type},
                )
            )
        failures = self.failure_store.search_failures(problem_id=problem_id, query=query, top_k=top_k)
        for idx, failure in enumerate(failures):
            docs.append(
                (
                    f"failure_{idx}",
                    "failure",
                    failure.get("reason_failed", ""),
                    failure,
                )
            )

        keyword_hits = self.keyword.retrieve(query=query, docs=docs, top_k=top_k)
        if not self.embeddings.available():
            return keyword_hits[:top_k]
        emb_hits = self.embeddings.retrieve(query=query, tags=tags, top_k=top_k)

        merged: dict[tuple[str, str], RetrievedItem] = {}
        for hit in keyword_hits + emb_hits:
            key = (hit.item_id, hit.item_type)
            if key not in merged or hit.score > merged[key].score:
                merged[key] = hit
        out = sorted(merged.values(), key=lambda x: x.score, reverse=True)
        return out[:top_k]
