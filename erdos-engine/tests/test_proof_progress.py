from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState
from erdos_engine.search.proof_progress import mechanism_hash, stage_gate_decision


def _problem() -> Problem:
    return Problem(
        id="erdos_004",
        title="t",
        statement="s",
        tags=["prime-gaps"],
        status="open",
        formalizable=True,
    )


def test_mechanism_hash_same_for_wording_variants() -> None:
    a = ProofMove(
        id="a",
        move_type="reduction",
        claim="wording one",
        mechanism_core_construction="crt covering",
        mechanism_asymptotic_regime="iterated logs",
        mechanism_bottleneck_attacked="coverage",
    )
    b = ProofMove(
        id="b",
        move_type="reduction",
        claim="wording two",
        mechanism_core_construction="crt covering",
        mechanism_asymptotic_regime="iterated logs",
        mechanism_bottleneck_attacked="coverage",
    )
    assert mechanism_hash(a) == mechanism_hash(b)


def test_stage_gate_blocks_without_previous_stage() -> None:
    move = ProofMove(
        id="m",
        move_type="reduction",
        claim="crt cover construction",
        target_milestone="crt_covering",
        lean_obligations=[{"statement": "forall n, n > 0 -> n >= 0"}],
    )
    state = ResearchState(id="s", problem_id="erdos_004")
    decision = stage_gate_decision(_problem(), state, move)
    assert not decision.allowed


def test_stage_gate_allows_after_previous_stage() -> None:
    prev = ProofMove(
        id="p",
        move_type="reduction",
        claim="interval reduction with logs",
        target_milestone="reduction_interval_to_gap",
    )
    evaln = MoveEvaluation(
        move_id="p",
        status="verified_formally",
        reason="ok",
        evidence={},
    )
    move = ProofMove(
        id="m",
        move_type="construction",
        claim="crt cover construction",
        target_milestone="crt_covering",
        lean_obligations=[{"statement": "forall n, n > 0 -> n >= 0"}],
    )
    state = ResearchState(
        id="s",
        problem_id="erdos_004",
        moves=[prev],
        evaluations=[evaln],
        assumptions=["stage:interval", "stage:gap_transfer"],
    )
    decision = stage_gate_decision(_problem(), state, move)
    assert decision.allowed
