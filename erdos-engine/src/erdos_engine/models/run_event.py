"""Run event model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


RunEventType = Literal[
    "run_started",
    "retrieval",
    "move_proposed",
    "move_evaluated",
    "stall_detected",
    "rlm_started",
    "candidate_move_ranked",
    "rlm_injected",
    "status_changed",
    "error",
    "run_finished",
]


class RunEvent(BaseModel):
    """One append-only run event."""

    event_type: RunEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    depth: int | None = None
    state_id: str | None = None
    payload: dict = Field(default_factory=dict)
