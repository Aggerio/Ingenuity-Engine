"""Graph checker using networkx."""

from __future__ import annotations

from itertools import combinations

import networkx as nx

from erdos_engine.checkers.base import BaseChecker
from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState


class GraphChecker(BaseChecker):
    """Finite graph sanity checks for small combinatorial claims."""

    name = "graph"

    def supports(self, problem: Problem, move: ProofMove) -> bool:
        text = f"{problem.title} {problem.statement} {move.claim}".lower()
        return any(k in text for k in ["graph", "ramsey", "triangle", "independent", "k6"])

    @staticmethod
    def is_triangle_free(g: nx.Graph) -> bool:
        for u, v, w in combinations(g.nodes, 3):
            if g.has_edge(u, v) and g.has_edge(v, w) and g.has_edge(u, w):
                return False
        return True

    def _ramsey_r33_check(self) -> dict:
        # finite search over 2-colorings of K6 edges
        nodes = list(range(6))
        edges = list(combinations(nodes, 2))
        total = 1 << len(edges)
        for mask in range(total):
            red = nx.Graph()
            blue = nx.Graph()
            red.add_nodes_from(nodes)
            blue.add_nodes_from(nodes)
            for idx, (u, v) in enumerate(edges):
                if (mask >> idx) & 1:
                    red.add_edge(u, v)
                else:
                    blue.add_edge(u, v)
            if self.is_triangle_free(red) and self.is_triangle_free(blue):
                return {
                    "holds": False,
                    "counterexample_mask": mask,
                }
        return {"holds": True}

    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        text = f"{problem.statement} {move.claim}".lower()
        if "r(3,3)" in text or "k6" in text or "triangle" in text:
            result = self._ramsey_r33_check()
            if result.get("holds"):
                return MoveEvaluation(
                    move_id=move.id,
                    status="accepted_computationally",
                    reason="Exhaustive K6 2-coloring finite check supports claim.",
                    score_delta=1.0,
                    evidence=result,
                )
            return MoveEvaluation(
                move_id=move.id,
                status="rejected_by_counterexample",
                reason="Found coloring with no monochromatic triangle.",
                score_delta=-3.0,
                evidence=result,
                counterexample=str(result.get("counterexample_mask")),
            )

        return MoveEvaluation(
            move_id=move.id,
            status="unsupported",
            reason="Graph checker found no suitable finite experiment.",
            score_delta=-0.5,
            evidence={},
        )
