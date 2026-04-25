"""Typed theorem graph models for compositional reasoning."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


TrustLevel = Literal["low", "medium", "high"]
ProofStatus = Literal["unverified", "verified", "rejected"]
NodeKind = Literal["candidate", "formalized"]
RuleType = Literal[
    "rewrite",
    "substitute",
    "bound_transfer",
    "specialization",
    "composition",
    "congruence_composition",
]


class ProofArtifact(BaseModel):
    """External proof artifact linked to theorem graph objects."""

    artifact_id: str = Field(min_length=1)
    lean_theorem_name: str = ""
    lean_artifact_path: str = ""
    content_hash: str = ""
    status: ProofStatus = "unverified"
    detail: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class TheoremNode(BaseModel):
    """Canonical theorem node for compositional planning."""

    node_id: str = Field(min_length=1)
    source_id: str = ""
    statement: str = Field(min_length=1)
    normalized_statement: str = Field(min_length=1)
    domain: str = "generic"
    kind: NodeKind = "candidate"
    symbols: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    conclusion: str = ""
    quantifiers: list[str] = Field(default_factory=list)
    trust_level: TrustLevel = "low"
    trust_score: float = 0.0
    proof_status: ProofStatus = "unverified"
    proof_artifacts: list[ProofArtifact] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class LeanObligation(BaseModel):
    """Lean obligation generated from edge application."""

    obligation_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    source_edge_id: str = ""
    source_node_ids: list[str] = Field(default_factory=list)
    status: ProofStatus = "unverified"
    detail: str = ""


class DerivationEdge(BaseModel):
    """Typed derivation edge connecting theorem nodes."""

    edge_id: str = Field(min_length=1)
    from_node_ids: list[str] = Field(default_factory=list)
    to_node_id: str = ""
    rule_type: RuleType
    preconditions: list[str] = Field(default_factory=list)
    generated_obligations: list[LeanObligation] = Field(default_factory=list)
    trust_level: TrustLevel = "low"
    trust_score: float = 0.0
    proof_status: ProofStatus = "unverified"
    metadata: dict = Field(default_factory=dict)


class DerivationChain(BaseModel):
    """Candidate composition chain used during search planning."""

    chain_id: str = Field(min_length=1)
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    composability_score: float = 0.0
    generated_obligations: list[LeanObligation] = Field(default_factory=list)
    summary: str = ""
