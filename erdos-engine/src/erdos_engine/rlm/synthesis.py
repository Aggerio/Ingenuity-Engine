"""Synthesis utilities for RLM outputs."""

from __future__ import annotations

import re

from erdos_engine.models import ProofMove


def _claim_fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    normalized = re.sub(r"[^a-z0-9 ]", "", normalized)
    return normalized[:240]


def _is_actionable(move: ProofMove) -> bool:
    if not move.test_plan or not move.test_plan.strip():
        return False
    low_signal_risk = (move.risk or "").lower()
    low_signal_rationale = (move.rationale or "").lower()
    vague_markers = ["unclear", "unknown", "vague", "unsure"]
    if any(marker in low_signal_risk for marker in vague_markers):
        return False
    if any(marker in low_signal_rationale for marker in vague_markers):
        return False
    return True


def dedupe_moves(moves: list[ProofMove]) -> list[ProofMove]:
    """Filter + deduplicate by move type and normalized claim fingerprint."""
    seen: set[tuple[str, str]] = set()
    out: list[ProofMove] = []
    for move in moves:
        if not _is_actionable(move):
            continue
        key = (move.move_type, _claim_fingerprint(move.claim))
        if key in seen:
            continue
        seen.add(key)
        out.append(move)
    return out
