"""Reducer for run events."""

from __future__ import annotations

from erdos_engine.models import ResearchState, RunEvent


def reduce_run_events(events: list[RunEvent]) -> dict:
    """Derive reduced run state from event stream."""
    status = "failed"
    best_state_payload: dict | None = None
    best_score = float("-inf")
    score_trajectory: list[float] = []
    rlm_notes: dict = {}

    for event in events:
        payload = event.payload
        if event.event_type == "status_changed":
            status = str(payload.get("status", status))
        elif event.event_type == "move_evaluated":
            state_payload = payload.get("state") or {}
            score = float(state_payload.get("score", payload.get("score", 0.0)))
            score_trajectory.append(score)
            if score > best_score:
                best_score = score
                best_state_payload = state_payload
        elif event.event_type == "rlm_started":
            rlm_notes.update({"failure_analysis": payload.get("failure_analysis", "")})
        elif event.event_type == "run_finished":
            status = str(payload.get("status", status))
            if isinstance(payload.get("rlm_notes"), dict):
                rlm_notes.update(payload["rlm_notes"])

    best_state = ResearchState(**best_state_payload) if best_state_payload else None
    return {
        "status": status,
        "best_state": best_state,
        "score_trajectory": score_trajectory,
        "rlm_notes": rlm_notes,
    }
