"""Move models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MoveType = Literal[
    "auxiliary_lemma",
    "reformulation",
    "reduction",
    "construction",
    "counterexample_search",
    "brute_force_experiment",
    "known_theorem_analogy",
    "proof_skeleton_step",
    "extremal_example",
    "external_theorem_anchor",
]


class ProofMove(BaseModel):
    """Candidate mathematical move."""

    id: str = Field(min_length=1)
    move_type: MoveType
    claim: str = Field(min_length=1)
    rationale: str = ""
    test_plan: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    expected_effect: str = ""
    risk: str | None = None
    source: Literal["llm", "lemma_db", "rlm", "human", "known_solution"] = "llm"

    # Case-based reasoning fields
    matched_prior_case_ids: list[str] = Field(default_factory=list)
    why_this_applies_here: str = ""
    required_preconditions: list[str] = Field(default_factory=list)
    how_to_falsify_fast: str = ""
    target_milestone: str | None = None
    theorem_chain_ids: list[str] = Field(default_factory=list)
    lean_obligations: list[dict] = Field(default_factory=list)
    source_quality: Literal["high", "medium", "low", "unknown"] = "unknown"
    exact_asymptotic_form: str | None = None
    translation_steps: list[str] = Field(default_factory=list)
    mechanism_core_construction: str = ""
    mechanism_asymptotic_regime: str = ""
    mechanism_bottleneck_attacked: str = ""
    progress_certificates: list[dict] = Field(default_factory=list)


class MoveEvaluation(BaseModel):
    """Evaluation result for one move."""

    move_id: str
    status: Literal[
        "accepted_computationally",
        "rejected_by_counterexample",
        "plausible_informal",
        "invalid_format",
        "unsupported",
        "verified_formally",
        "already_known",
    ]
    score_delta: float = 0.0
    reason: str
    evidence: dict = Field(default_factory=dict)
    counterexample: str | None = None
