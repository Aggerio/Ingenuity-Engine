"""Algebra checker using sympy."""

from __future__ import annotations

import sympy as sp

from erdos_engine.checkers.base import BaseChecker
from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState


class AlgebraChecker(BaseChecker):
    """Symbolic simplification checker for simple identities/equalities."""

    name = "algebra"

    def supports(self, problem: Problem, move: ProofMove) -> bool:
        text = f"{move.claim} {move.test_plan or ''}".lower()
        return any(k in text for k in ["=", "identity", "simplify", "factor", "expand"])

    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        claim = move.claim
        if "=" not in claim:
            return MoveEvaluation(
                move_id=move.id,
                status="unsupported",
                reason="No equality found for symbolic check.",
                score_delta=-0.5,
                evidence={},
            )
        left, right = claim.split("=", maxsplit=1)
        try:
            l_expr = sp.sympify(left.strip())
            r_expr = sp.sympify(right.strip())
            diff = sp.simplify(l_expr - r_expr)
        except Exception as exc:  # noqa: BLE001
            return MoveEvaluation(
                move_id=move.id,
                status="unsupported",
                reason=f"Symbolic parse failed: {exc}",
                score_delta=-0.5,
                evidence={},
            )
        if diff == 0:
            return MoveEvaluation(
                move_id=move.id,
                status="accepted_computationally",
                reason="Sympy simplification confirms equality.",
                score_delta=1.0,
                evidence={"simplified_difference": "0"},
            )
        return MoveEvaluation(
            move_id=move.id,
            status="rejected_by_counterexample",
            reason="Sympy simplification indicates non-zero difference.",
            score_delta=-2.0,
            evidence={"simplified_difference": str(diff)},
            counterexample=str(diff),
        )
