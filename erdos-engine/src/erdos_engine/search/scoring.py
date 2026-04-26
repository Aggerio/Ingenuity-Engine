"""Scoring utilities for move evaluations and research states."""

from __future__ import annotations

from erdos_engine.models import MoveEvaluation, ProofMove


def score_move_evaluation(
    evaluation: MoveEvaluation,
    move: ProofMove,
    *,
    has_progress_certificate: bool = False,
) -> float:
    """Score one move result using configured v0 heuristics."""
    base = {
        "verified_formally": 10.0,
        "accepted_computationally": 5.0,
        "already_known": 3.0,
        "plausible_informal": 2.0,
        "rejected_by_counterexample": -5.0,
        "invalid_format": -3.0,
        "unsupported": -2.0,
    }.get(evaluation.status, 0.0)

    bonus = 0.0
    if move.test_plan:
        bonus += 1.0
    if "lemma" in move.expected_effect.lower() or "reduce" in move.expected_effect.lower():
        bonus += 2.0
    if move.risk and "vague" in move.risk.lower():
        bonus -= 2.0
    if not has_progress_certificate:
        bonus -= 3.0
    return base + bonus + evaluation.score_delta


def score_state(
    previous_score: float,
    move_scores: list[float],
    depth: int,
    novelty: float = 0.0,
    *,
    repeated_mechanism: bool = False,
) -> float:
    """Aggregate state score with depth penalty and novelty bonus."""
    repeat_penalty = 2.0 if repeated_mechanism else 0.0
    return previous_score + sum(move_scores) + novelty - (0.5 * depth) - repeat_penalty
