"""Checker base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState


class BaseChecker(ABC):
    """Interface for move evaluators."""

    name: str = "base"

    @abstractmethod
    def supports(self, problem: Problem, move: ProofMove) -> bool:
        """Whether this checker can evaluate the move for the problem."""

    @abstractmethod
    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        """Evaluate one move in context."""
