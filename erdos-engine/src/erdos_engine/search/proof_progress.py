"""Proof-progress policies: stage gates, mechanisms, and obligations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState

ERDOS004_STAGES = [
    "interval",
    "gap_transfer",
    "covering_existence",
    "parameter_growth_bridge",
]

CERTIFICATE_TYPES = {
    "new_inequality",
    "new_parameter_relation",
    "improved_coverage_bound",
}

_TAUTOLOGY_PATTERNS = [
    re.compile(r"^\s*a\s*=\s*a\s*$", re.IGNORECASE),
    re.compile(r"^\s*x\s*=\s*x\s*$", re.IGNORECASE),
    re.compile(r"^\s*prove\s+the\s+statement\s*$", re.IGNORECASE),
    re.compile(r"^\s*assume\s+.*\s+therefore\s+.*\s*$", re.IGNORECASE),
]


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class DiagnosticResult:
    ok: bool
    reason: str


def mechanism_hash(move: ProofMove) -> str:
    payload = "|".join(
        [
            (move.mechanism_core_construction or move.move_type).strip().lower(),
            (move.mechanism_asymptotic_regime or move.target_milestone or "").strip().lower(),
            (move.mechanism_bottleneck_attacked or move.expected_effect or "").strip().lower(),
        ]
    )
    normalized = re.sub(r"\s+", " ", payload)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def required_stage_for_move(problem: Problem, move: ProofMove) -> str | None:
    if problem.id != "erdos_004":
        return None
    milestone = (move.target_milestone or "").strip().lower()
    claim_text = " ".join([move.claim, move.rationale or "", move.expected_effect or ""]).lower()
    if "interval" in milestone or "interval" in claim_text:
        return "interval"
    if "gap" in milestone or "pi(" in claim_text or "p_{n+1}" in claim_text or "p_n" in claim_text:
        return "gap_transfer"
    if "cover" in milestone or "crt" in milestone or "congruence" in claim_text:
        return "covering_existence"
    if "bridge" in milestone or "growth" in milestone or "log" in claim_text:
        return "parameter_growth_bridge"
    return None


def _infer_stage_from_move(move: ProofMove) -> str | None:
    milestone = (move.target_milestone or "").strip().lower()
    text = " ".join([move.claim, move.rationale or "", move.expected_effect or ""]).lower()
    if "interval" in milestone or "interval" in text:
        return "interval"
    if "gap" in milestone or "pi(" in text or "p_{n+1}" in text or "p_n" in text:
        return "gap_transfer"
    if "cover" in milestone or "crt" in milestone or "congruence" in text:
        return "covering_existence"
    if "bridge" in milestone or "growth" in milestone or "log" in text:
        return "parameter_growth_bridge"
    return None


def non_tautological_accepted_stages(state: ResearchState) -> set[str]:
    out: set[str] = set()
    for idx, move in enumerate(state.moves):
        if idx >= len(state.evaluations):
            break
        evaluation = state.evaluations[idx]
        if evaluation.status not in {"verified_formally", "accepted_computationally", "already_known"}:
            continue
        if evaluation.evidence.get("rejection_category") == "tautological_mapping_blocked":
            continue
        marker = f"stage:{_infer_stage_from_move(move) or ''}"
        if marker != "stage:":
            out.add(marker.split(":", 1)[1])
    for assumption in state.assumptions:
        if assumption.startswith("stage:"):
            out.add(assumption.split(":", 1)[1])
    return out


def stage_gate_decision(problem: Problem, state: ResearchState, move: ProofMove) -> GateDecision:
    stage = required_stage_for_move(problem, move)
    if stage is None:
        return GateDecision(True, "")
    ordered = ERDOS004_STAGES
    index = ordered.index(stage)
    if index == 0:
        return GateDecision(True, "")
    accepted = non_tautological_accepted_stages(state)
    prereq = ordered[index - 1]
    if prereq not in accepted:
        return GateDecision(False, f"stage_gate_blocked:{stage}:missing_prereq:{prereq}")
    return GateDecision(True, "")


def obligation_templates_ok(move: ProofMove) -> GateDecision:
    obligations = move.lean_obligations or []
    if move.move_type == "external_theorem_anchor":
        if not move.exact_asymptotic_form:
            return GateDecision(False, "missing_exact_asymptotic_form")
        if not move.translation_steps:
            return GateDecision(False, "missing_translation_steps")
    if not obligations:
        return GateDecision(False, "missing_obligations")
    has_nontrivial = False
    for obligation in obligations:
        statement = str(obligation.get("statement", "")).strip()
        if not statement:
            continue
        if any(pattern.match(statement) for pattern in _TAUTOLOGY_PATTERNS):
            return GateDecision(False, "tautological_obligation_pattern")
        if ("forall" in statement.lower() or "∃" in statement or "exists" in statement.lower()) and (
            "<" in statement or ">" in statement or "<=" in statement or ">=" in statement
        ):
            has_nontrivial = True
        if "->" in statement and "=" in statement:
            has_nontrivial = True
    if not has_nontrivial:
        return GateDecision(False, "no_nontrivial_obligation_shape")
    return GateDecision(True, "")


def progress_certificates_ok(move: ProofMove) -> bool:
    for certificate in move.progress_certificates:
        cert_type = str(certificate.get("type", "")).strip()
        if cert_type in CERTIFICATE_TYPES and str(certificate.get("statement", "")).strip():
            return True
    return False


def move_family_diagnostic(move: ProofMove) -> DiagnosticResult:
    text = " ".join([move.claim, move.test_plan or "", move.expected_effect]).lower()
    if "coverage" not in text:
        return DiagnosticResult(False, "diagnostic_fail:coverage_density")
    if not any(token in text for token in ["mod", "modulus", "coprime", "crt", "growth"]):
        return DiagnosticResult(False, "diagnostic_fail:modulus_growth_feasibility")
    if not any(token in text for token in ["log", "asymptotic", "inequality", "bound"]):
        return DiagnosticResult(False, "diagnostic_fail:asymptotic_gain_sanity")
    return DiagnosticResult(True, "")


def certified_stage_marker(problem: Problem, move: ProofMove, evaluation: MoveEvaluation) -> str | None:
    if evaluation.status not in {"verified_formally", "accepted_computationally", "already_known"}:
        return None
    if evaluation.evidence.get("rejection_category") == "tautological_mapping_blocked":
        return None
    if not progress_certificates_ok(move):
        return None
    stage = required_stage_for_move(problem, move)
    if not stage:
        return None
    return f"stage:{stage}"
