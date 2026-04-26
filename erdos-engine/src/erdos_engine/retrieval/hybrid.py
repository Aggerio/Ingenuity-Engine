"""Hybrid retriever combining keyword and optional embedding results."""

from __future__ import annotations

from erdos_engine.models import DerivationChain
from erdos_engine.models import RetrievedItem
from erdos_engine.retrieval.theorem_graph import TheoremGraphPlanner
from erdos_engine.retrieval.embeddings import EmbeddingsRetriever
from erdos_engine.retrieval.keyword import KeywordRetriever
from erdos_engine.store.failure_store import FailureStore
from erdos_engine.store.lemma_store import LemmaStore
from erdos_engine.store.theorem_graph_store import TheoremGraphStore


class HybridRetriever:
    """Combine retrieval from lemmas, proof moves, and failure memory."""

    def __init__(
        self,
        lemma_store: LemmaStore,
        failure_store: FailureStore,
        theorem_graph_store: TheoremGraphStore | None = None,
    ) -> None:
        self.lemma_store = lemma_store
        self.failure_store = failure_store
        self.theorem_graph_store = theorem_graph_store
        self.keyword = KeywordRetriever()
        self.embeddings = EmbeddingsRetriever()
        self._latest_chains: list[DerivationChain] = []

    @property
    def latest_chains(self) -> list[DerivationChain]:
        return list(self._latest_chains)

    def retrieve(self, query: str, tags: list[str], top_k: int, problem_id: str) -> list[RetrievedItem]:
        domain_first_tags = {t.lower() for t in tags}
        is_prime_gap = any(t in {"prime-gaps", "prime_gap", "prime", "sieve", "coverings", "pnt"} for t in domain_first_tags)
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
            if is_prime_gap:
                searchable = " ".join([move.claim, move.rationale, move.expected_effect]).lower()
                if not any(token in searchable for token in ["prime", "gap", "sieve", "cover", "pnt", "crt", "log"]):
                    continue
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

        self._latest_chains = []
        if self.theorem_graph_store is not None:
            nodes = self.theorem_graph_store.load_nodes()
            edges = self.theorem_graph_store.load_edges()
            planner = TheoremGraphPlanner(nodes, edges)
            domain_filter = {"number_theory"} if is_prime_gap else None
            chains = planner.propose_chains(
                query=query,
                top_k=max(3, top_k // 2),
                allowed_domains=domain_filter,
            )
            self._latest_chains = chains
            for chain in chains:
                docs.append(
                    (
                        chain.chain_id,
                        "theorem_chain",
                        chain.summary,
                        {
                            "edge_ids": chain.edge_ids,
                            "node_ids": chain.node_ids,
                            "composability_score": chain.composability_score,
                            "obligations": [obl.model_dump() for obl in chain.generated_obligations],
                        },
                    )
                )

        keyword_hits = self.keyword.retrieve(query=query, docs=docs, top_k=top_k)
        if is_prime_gap and not keyword_hits:
            # fallback to global index only when domain-scoped retrieval is empty
            return self.retrieve(query=query, tags=[], top_k=top_k, problem_id=problem_id)
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
