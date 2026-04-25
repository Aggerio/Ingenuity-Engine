from pathlib import Path

from erdos_engine.checkers.graph import GraphChecker
from erdos_engine.checkers.lean import LeanChecker
from erdos_engine.checkers.number_theory import divisors, gcd, is_prime, lcm, prime_factorization
from erdos_engine.models import Problem, ProofMove, ResearchState


def test_number_theory_utils() -> None:
    assert is_prime(2)
    assert is_prime(29)
    assert not is_prime(1)
    assert gcd(12, 18) == 6
    assert lcm(4, 6) == 12
    assert divisors(12) == [1, 2, 3, 4, 6, 12]
    assert prime_factorization(60) == {2: 2, 3: 1, 5: 1}


def test_graph_checker_ramsey_toy() -> None:
    checker = GraphChecker()
    result = checker._ramsey_r33_check()
    assert result["holds"] is True


def test_lean_checker_parses_mocked_failure(monkeypatch, tmp_path: Path) -> None:
    checker = LeanChecker(project_dir=tmp_path, timeout_seconds=2)
    p = Problem(
        id="p",
        title="t",
        statement="s",
        tags=[],
        status="solved",
        known_solution_path=None,
        source_url=None,
        difficulty_guess=None,
        computationally_testable=True,
        formalizable=True,
    )
    move = ProofMove(
        id="m1",
        move_type="reduction",
        claim="Assume interval (N, N+L] contains no primes; derive prime gap lower bound",
        rationale="",
        test_plan=None,
        dependencies=[],
        expected_effect="",
        risk=None,
        source="llm",
    )
    state = ResearchState(id="s", problem_id="p")

    class Proc:
        returncode = 1
        stdout = ""
        stderr = "type mismatch"

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Proc())
    ev = checker.evaluate(p, state, move)
    assert ev.status == "rejected_by_counterexample"
    assert ev.evidence["lean_formalization_attempted"] is True
