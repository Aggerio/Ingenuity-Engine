"""Specialized RLM agents sharing one base client."""

from __future__ import annotations

from dataclasses import dataclass

from erdos_engine.llm.base import LLMClient
from erdos_engine.models import Problem, ResearchState


@dataclass
class BaseAgent:
    name: str
    llm: LLMClient

    def run(self, problem: Problem, beam_states: list[ResearchState], failures: list[dict]) -> dict:
        prompt = (
            f"Agent={self.name}. Problem={problem.statement}. "
            f"States={len(beam_states)}. Failures={len(failures)}. "
            "Return JSON with short analysis and candidate moves."
        )
        return self.llm.critic_review(prompt)


class AnalogyAgent(BaseAgent):
    pass


class CounterexampleAgent(BaseAgent):
    pass


class ReformulationAgent(BaseAgent):
    pass


class ReductionAgent(BaseAgent):
    pass


class ConstructionAgent(BaseAgent):
    pass


class ProofSkeletonAgent(BaseAgent):
    pass
