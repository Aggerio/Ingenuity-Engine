"""Theorem graph planning and retrieval helpers."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from erdos_engine.ingestion.theorem_graph_bootstrap import extract_symbols, normalize_statement
from erdos_engine.models import DerivationChain, DerivationEdge, LeanObligation, TheoremNode


def _chain_id(seed: str) -> str:
    return "chain_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


class TheoremGraphPlanner:
    """Find short compositional chains from theorem graph."""

    def __init__(self, nodes: list[TheoremNode], edges: list[DerivationEdge]) -> None:
        self.nodes = nodes
        self.edges = edges
        self._nodes_by_id = {node.node_id: node for node in nodes}
        self._adj: dict[str, list[DerivationEdge]] = defaultdict(list)
        for edge in edges:
            for node_id in edge.from_node_ids:
                self._adj[node_id].append(edge)

    @staticmethod
    def _similarity(query_symbols: set[str], node: TheoremNode) -> float:
        node_symbols = set(node.symbols)
        if not query_symbols or not node_symbols:
            return 0.0
        overlap = len(query_symbols.intersection(node_symbols))
        return overlap / float(max(len(query_symbols), 1))

    def propose_chains(self, query: str, top_k: int = 5, max_hops: int = 2) -> list[DerivationChain]:
        query_norm = normalize_statement(query)
        query_symbols = set(extract_symbols(query_norm))
        if not self.nodes:
            return []

        start_nodes = sorted(
            self.nodes,
            key=lambda node: (self._similarity(query_symbols, node), node.trust_score),
            reverse=True,
        )[: max(top_k * 3, 10)]

        chains: list[DerivationChain] = []
        for start in start_nodes:
            base_score = self._similarity(query_symbols, start)
            if base_score <= 0:
                continue
            for edge in self._adj.get(start.node_id, []):
                target = self._nodes_by_id.get(edge.to_node_id) or start
                obligations = [
                    LeanObligation(
                        obligation_id=f"obl_{edge.edge_id}",
                        statement=f"{start.normalized_statement} -> {target.normalized_statement}",
                        source_edge_id=edge.edge_id,
                        source_node_ids=[start.node_id],
                    )
                ]
                score = base_score + edge.trust_score + target.trust_score
                chain = DerivationChain(
                    chain_id=_chain_id(f"{start.node_id}:{edge.edge_id}:{target.node_id}"),
                    node_ids=[start.node_id, target.node_id],
                    edge_ids=[edge.edge_id],
                    composability_score=score,
                    generated_obligations=obligations,
                    summary=f"{start.conclusion} --{edge.rule_type}--> {target.conclusion}",
                )
                chains.append(chain)

                if max_hops < 2:
                    continue
                for edge2 in self._adj.get(target.node_id, []):
                    target2 = self._nodes_by_id.get(edge2.to_node_id) or target
                    obligations2 = obligations + [
                        LeanObligation(
                            obligation_id=f"obl_{edge2.edge_id}",
                            statement=f"{target.normalized_statement} -> {target2.normalized_statement}",
                            source_edge_id=edge2.edge_id,
                            source_node_ids=[target.node_id],
                        )
                    ]
                    score2 = score + edge2.trust_score + target2.trust_score
                    chains.append(
                        DerivationChain(
                            chain_id=_chain_id(
                                f"{start.node_id}:{edge.edge_id}:{target.node_id}:{edge2.edge_id}:{target2.node_id}"
                            ),
                            node_ids=[start.node_id, target.node_id, target2.node_id],
                            edge_ids=[edge.edge_id, edge2.edge_id],
                            composability_score=score2,
                            generated_obligations=obligations2,
                            summary=(
                                f"{start.conclusion} --{edge.rule_type}--> {target.conclusion}"
                                f" --{edge2.rule_type}--> {target2.conclusion}"
                            ),
                        )
                    )

        chains.sort(key=lambda item: item.composability_score, reverse=True)
        # dedupe by edge signature
        seen: set[tuple[str, ...]] = set()
        out: list[DerivationChain] = []
        for chain in chains:
            sig = tuple(chain.edge_ids)
            if sig in seen:
                continue
            seen.add(sig)
            out.append(chain)
            if len(out) >= top_k:
                break
        return out
