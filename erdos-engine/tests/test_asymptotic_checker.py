from erdos_engine.checkers.asymptotic_dominance import AsymptoticDominanceChecker
from erdos_engine.models import Problem, ProofMove, ResearchState


def _problem() -> Problem:
    return Problem(id="erdos_004", title="t", statement="s", tags=["prime-gaps"], status="open", formalizable=True)


def test_asymptotic_checker_accepts_simple_dominance() -> None:
    checker = AsymptoticDominanceChecker()
    move = ProofMove(
        id="m1",
        move_type="auxiliary_lemma",
        claim="log_2(n) <= log_2(n)",
        exact_asymptotic_form="log_2(n) <= log_2(n)",
    )
    out = checker.evaluate(_problem(), ResearchState(id="s", problem_id="erdos_004"), move)
    assert out.status in {"accepted_computationally", "already_known"}


def test_asymptotic_checker_rejects_reverse_dominance() -> None:
    checker = AsymptoticDominanceChecker()
    move = ProofMove(
        id="m2",
        move_type="auxiliary_lemma",
        claim="log_2(n) > log_2(n) log_3(n)",
        exact_asymptotic_form="log_2(n) > log_2(n) log_3(n)",
    )
    out = checker.evaluate(_problem(), ResearchState(id="s", problem_id="erdos_004"), move)
    assert out.status == "rejected_by_counterexample"
