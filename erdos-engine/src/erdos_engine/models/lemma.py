"""Lemma model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Lemma(BaseModel):
    """Known lemma or pattern stored in local DB."""

    id: str = Field(min_length=1)
    title: str
    statement: str
    domain_tags: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    conclusion: str
    proof_strategy: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    used_in: list[str] = Field(default_factory=list)
    source: str | None = None
    formal_status: Literal["informal", "computational", "formal"] = "informal"
    failure_modes: list[str] = Field(default_factory=list)

    # Why-worked schema for transfer learning
    preconditions: list[str] = Field(default_factory=list)
    mechanism_of_success: str = ""
    transferability_conditions: list[str] = Field(default_factory=list)
    known_failure_modes: list[str] = Field(default_factory=list)
