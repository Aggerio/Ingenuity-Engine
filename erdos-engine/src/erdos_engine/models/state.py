"""Research state models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .move import MoveEvaluation, ProofMove


class RetrievedItem(BaseModel):
    """An item retrieved from memory stores."""

    item_id: str
    item_type: str
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class ResearchState(BaseModel):
    """One node in beam search."""

    id: str
    problem_id: str
    depth: int = 0
    subgoals: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    accepted_claims: list[str] = Field(default_factory=list)
    rejected_claims: list[str] = Field(default_factory=list)
    retrieved_lemmas: list[str] = Field(default_factory=list)
    moves: list[ProofMove] = Field(default_factory=list)
    evaluations: list[MoveEvaluation] = Field(default_factory=list)
    experiments: list[dict] = Field(default_factory=list)
    score: float = 0.0
    trace: list[str] = Field(default_factory=list)
    stalled_steps: int = 0


class RLMOutput(BaseModel):
    """Output from recursive research mode."""

    failure_analysis: str = ""
    reformulations: list[str] = Field(default_factory=list)
    subproblems: list[str] = Field(default_factory=list)
    candidate_moves: list[ProofMove] = Field(default_factory=list)
    recommended_next_search_bias: str = ""

    # Lemma-factory buckets
    bridge_lemmas: list[ProofMove] = Field(default_factory=list)
    blocker_lemmas: list[ProofMove] = Field(default_factory=list)
    validator_lemmas: list[ProofMove] = Field(default_factory=list)
