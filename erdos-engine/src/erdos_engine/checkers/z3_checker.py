"""Optional z3 checker."""

from __future__ import annotations

from erdos_engine.checkers.base import BaseChecker
from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState

try:
    import z3  # type: ignore
except Exception:  # noqa: BLE001
    z3 = None


class Z3Checker(BaseChecker):
    """Disabled unless z3-solver is installed."""

    name = "z3"

    def supports(self, problem: Problem, move: ProofMove) -> bool:
        return z3 is not None and "z3" in (move.test_plan or "").lower()

    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        if z3 is None:
            return MoveEvaluation(
                move_id=move.id,
                status="unsupported",
                reason="z3-solver is not installed.",
                score_delta=-0.5,
                evidence={},
            )
        return MoveEvaluation(
            move_id=move.id,
            status="plausible_informal",
            reason="z3 checker hook present; custom encodings are future work.",
            score_delta=0.0,
            evidence={},
        )
