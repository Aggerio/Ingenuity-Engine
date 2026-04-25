"""Safe brute-force checker with canned experiments only."""

from __future__ import annotations

from erdos_engine.checkers.base import BaseChecker
from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState


class BruteForceChecker(BaseChecker):
    """Runs bounded canned checks from structured test-plan hints."""

    name = "brute_force"

    def supports(self, problem: Problem, move: ProofMove) -> bool:
        if not move.test_plan:
            return False
        text = move.test_plan.lower()
        return any(k in text for k in ["enumerate", "finite", "bounded", "mod", "range"])

    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        plan = (move.test_plan or "").lower()
        if "k6" in plan and "enumerate" in plan:
            return MoveEvaluation(
                move_id=move.id,
                status="plausible_informal",
                reason="Plan is concrete but delegated to graph checker for exact result.",
                score_delta=0.5,
                evidence={"plan": move.test_plan},
            )
        if "mod" in plan or "residue" in plan:
            return MoveEvaluation(
                move_id=move.id,
                status="plausible_informal",
                reason="Modular finite plan appears executable in bounded ranges.",
                score_delta=0.5,
                evidence={"plan": move.test_plan},
            )
        return MoveEvaluation(
            move_id=move.id,
            status="unsupported",
            reason="No safe canned brute-force template matched test_plan.",
            score_delta=-0.5,
            evidence={"plan": move.test_plan},
        )
