"""Symbolic asymptotic-dominance checker for iterated logs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from erdos_engine.checkers.base import BaseChecker
from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState


@dataclass(frozen=True)
class _ComplexityTerm:
    log2_exp: int = 0
    log3_exp: int = 0
    log4_exp: int = 0
    constant: float = 1.0


class AsymptoticDominanceChecker(BaseChecker):
    """Evaluate simple eventual inequalities over iterated logarithms."""

    name = "asymptotic_dominance"

    _PATTERN = re.compile(r"(.+?)(<=|>=|<|>)(.+)")

    def supports(self, problem: Problem, move: ProofMove) -> bool:
        text = " ".join([move.claim, move.exact_asymptotic_form or ""]).lower()
        return any(token in text for token in ["log_2", "log_3", "log_4", "iterated log", "asymptotic"])

    def _parse_term(self, expr: str) -> _ComplexityTerm:
        low = expr.lower().replace(" ", "")
        c = 1.0
        const_match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\*", low)
        if const_match:
            c = float(const_match.group(1))
            low = low[len(const_match.group(0)) :]
        return _ComplexityTerm(
            log2_exp=low.count("log_2"),
            log3_exp=low.count("log_3"),
            log4_exp=low.count("log_4"),
            constant=c,
        )

    @staticmethod
    def _dominates(lhs: _ComplexityTerm, rhs: _ComplexityTerm) -> bool:
        lhs_sig = (lhs.log2_exp, lhs.log3_exp, lhs.log4_exp, lhs.constant)
        rhs_sig = (rhs.log2_exp, rhs.log3_exp, rhs.log4_exp, rhs.constant)
        return lhs_sig <= rhs_sig

    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        text = (move.exact_asymptotic_form or move.claim).replace("≤", "<=").replace("≥", ">=")
        parsed = self._PATTERN.search(text)
        if not parsed:
            return MoveEvaluation(
                move_id=move.id,
                status="unsupported",
                reason="No parsable asymptotic inequality found.",
                score_delta=0.0,
                evidence={"checker": self.name, "rejection_category": "asymptotic_parse_failed"},
            )
        lhs_raw, op, rhs_raw = parsed.group(1), parsed.group(2), parsed.group(3)
        lhs, rhs = self._parse_term(lhs_raw), self._parse_term(rhs_raw)
        ok = self._dominates(lhs, rhs) if op in {"<=", "<"} else self._dominates(rhs, lhs)
        if ok:
            return MoveEvaluation(
                move_id=move.id,
                status="accepted_computationally",
                reason="Asymptotic dominance holds for iterated-log term ordering.",
                score_delta=2.0,
                evidence={
                    "checker": self.name,
                    "certificate_type": "new_inequality",
                    "lhs": lhs.__dict__,
                    "rhs": rhs.__dict__,
                },
            )
        return MoveEvaluation(
            move_id=move.id,
            status="rejected_by_counterexample",
            reason="Asymptotic dominance ordering does not hold.",
            score_delta=-2.0,
            evidence={"checker": self.name, "lhs": lhs.__dict__, "rhs": rhs.__dict__},
            counterexample=f"{lhs_raw.strip()} !{op} {rhs_raw.strip()}",
        )
