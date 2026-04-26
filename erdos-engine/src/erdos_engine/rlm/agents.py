"""Specialized RLM agents sharing one base client."""

from __future__ import annotations

import json
from dataclasses import dataclass

from erdos_engine.llm.base import LLMClient
from erdos_engine.models import Problem, ResearchState


@dataclass
class BaseAgent:
    name: str
    llm: LLMClient

    def run(
        self,
        problem: Problem,
        beam_states: list[ResearchState],
        failures: list[dict],
        search_signals: dict | None = None,
    ) -> dict:
        sig = ""
        if search_signals:
            dumped = json.dumps(search_signals, ensure_ascii=False)
            if len(dumped) > 3500:
                dumped = dumped[:3500] + "…"
            sig = f" StallSignals={dumped}"
        prompt = (
            f"Agent={self.name}. Problem={problem.statement}. "
            f"States={len(beam_states)}. Failures={len(failures)}.{sig} "
            "Return JSON with short analysis and candidate_moves tailored to StallSignals when present."
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
