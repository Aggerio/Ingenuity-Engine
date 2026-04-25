"""Problem model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Problem(BaseModel):
    """An Erdős-style research problem."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    status: Literal["solved", "open"]
    known_solution_path: str | None = None
    source_url: str | None = None
    difficulty_guess: str | None = None
    computationally_testable: bool = True
    formalizable: bool = True
