"""LLM client interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from erdos_engine.models import ProofMove, RLMOutput


class LLMClient(ABC):
    """Interface for move proposal and recursive-research generations."""

    @abstractmethod
    def generate_moves(self, prompt: str, n: int) -> list[ProofMove]:
        """Generate candidate proof moves."""

    @abstractmethod
    def generate_rlm(self, prompt: str) -> RLMOutput:
        """Generate recursive research bundle."""

    @abstractmethod
    def critic_review(self, prompt: str) -> dict:
        """Generate skeptical critic analysis."""
