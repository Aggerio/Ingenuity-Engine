"""Stall detection helpers."""

from __future__ import annotations


def is_stalled(best_scores: list[float], threshold: int) -> bool:
    """Detect stall when no strict improvement for threshold windows."""
    if len(best_scores) < threshold + 1:
        return False
    tail = best_scores[-(threshold + 1) :]
    return max(tail) <= tail[0]


def is_semantically_stalled(novelty_scores: list[float], threshold: int) -> bool:
    """Detect semantic stall when recent novelty remains very low."""
    if len(novelty_scores) < threshold:
        return False
    tail = novelty_scores[-threshold:]
    return sum(tail) / float(threshold) < 0.05
