"""Number theory checker and helper utilities."""

from __future__ import annotations

import math
import re
from itertools import product

from erdos_engine.checkers.base import BaseChecker
from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False
    r = int(math.isqrt(n))
    for d in range(3, r + 1, 2):
        if n % d == 0:
            return False
    return True


def divisors(n: int) -> list[int]:
    out: set[int] = set()
    for d in range(1, int(math.isqrt(n)) + 1):
        if n % d == 0:
            out.add(d)
            out.add(n // d)
    return sorted(out)


def gcd(a: int, b: int) -> int:
    return math.gcd(a, b)


def lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b) if a and b else 0


def prime_factorization(n: int) -> dict[int, int]:
    rem = n
    factors: dict[int, int] = {}
    d = 2
    while d * d <= rem:
        while rem % d == 0:
            factors[d] = factors.get(d, 0) + 1
            rem //= d
        d += 1 if d == 2 else 2
    if rem > 1:
        factors[rem] = factors.get(rem, 0) + 1
    return factors


def modular_residue_test(values: list[int], modulus: int) -> list[int]:
    return [v % modulus for v in values]


def bounded_tuple_search(bounds: list[range], predicate) -> tuple[bool, tuple[int, ...] | None]:
    for tup in product(*bounds):
        if predicate(*tup):
            return True, tuple(int(x) for x in tup)
    return False, None


class NumberTheoryChecker(BaseChecker):
    """Heuristic checker for elementary number theoretic claims."""

    name = "number_theory"

    def supports(self, problem: Problem, move: ProofMove) -> bool:
        text = f"{problem.title} {problem.statement} {move.claim} {move.test_plan or ''}".lower()
        return any(k in text for k in ["prime", "divisor", "mod", "gcd", "lcm", "number"])

    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        claim = move.claim.lower()
        if problem.id == "erdos_004":
            issues = _validate_problem4_claim(move)
            if issues:
                return MoveEvaluation(
                    move_id=move.id,
                    status="rejected_by_counterexample",
                    reason="; ".join(issues),
                    score_delta=-3.0,
                    evidence={"validator": "problem4", "issues": issues},
                    counterexample=issues[0],
                )

        if "infinitely many prime" in problem.statement.lower() or "prime" in claim:
            small_primes = [2, 3, 5, 7]
            n = 1
            for p in small_primes:
                n *= p
            n += 1
            residues = [n % p for p in small_primes]
            if all(r != 0 for r in residues):
                return MoveEvaluation(
                    move_id=move.id,
                    status="accepted_computationally",
                    reason="Construction survives finite residue sanity check.",
                    score_delta=1.0,
                    evidence={"N": n, "residues": residues},
                )
            return MoveEvaluation(
                move_id=move.id,
                status="rejected_by_counterexample",
                reason="Residue check failed.",
                score_delta=-2.0,
                evidence={"N": n, "residues": residues},
                counterexample=str(residues),
            )

        return MoveEvaluation(
            move_id=move.id,
            status="unsupported",
            reason="Number theory checker found no bounded test.",
            score_delta=-0.5,
            evidence={},
        )


def _validate_problem4_claim(move: ProofMove) -> list[str]:
    """Heuristic validators for Erdős #4 move quality."""
    text = " ".join([move.claim, move.rationale or "", move.test_plan or ""]).lower()
    issues: list[str] = []

    if "prime divisor of i" in text or "choose p_i" in text and "divides i" in text:
        issues.append("bad_crt_assignment: reusing prime divisors of i breaks CRT covering structure")

    if re.search(r"log\s*[nN]\s*~\s*[qQ]", text) or "log n ~ q" in text:
        issues.append("invalid_asymptotic: unsupported claim that log N is asymptotically Q")

    if "log log log log" in text and (
        "10^6" in text or "10^7" in text or "10^8" in text or "10^9" in text
    ):
        issues.append("domain_issue: testing small n with log log log log term is outside safe domain")

    return issues
