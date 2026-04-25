"""Recursive research harness invoked on beam stall."""

from __future__ import annotations

from erdos_engine.llm.base import LLMClient
from erdos_engine.llm.prompts import build_rlm_prompt
from erdos_engine.models import Problem, RLMOutput, ResearchState
from erdos_engine.rlm.agents import (
    AnalogyAgent,
    ConstructionAgent,
    CounterexampleAgent,
    ProofSkeletonAgent,
    ReductionAgent,
    ReformulationAgent,
)
from erdos_engine.rlm.synthesis import dedupe_moves


class RLMHarness:
    """Coordinates recursive research mode generation and synthesis."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def run(
        self,
        problem: Problem,
        beam_states: list[ResearchState],
        failures: list[dict],
        solved_cases: list[dict],
    ) -> RLMOutput:
        prompt = build_rlm_prompt(
            problem=problem,
            beam_states=beam_states,
            failures=failures,
            solved_cases=solved_cases,
        )
        base = self.llm.generate_rlm(prompt)

        agents = [
            AnalogyAgent("analogy", self.llm),
            CounterexampleAgent("counterexample", self.llm),
            ReformulationAgent("reformulation", self.llm),
            ReductionAgent("reduction", self.llm),
            ConstructionAgent("construction", self.llm),
            ProofSkeletonAgent("proof_skeleton", self.llm),
        ]
        notes = []
        for agent in agents:
            out = agent.run(problem, beam_states, failures)
            if out:
                notes.append(f"{agent.name}: {out}")

        base.bridge_lemmas = dedupe_moves(base.bridge_lemmas)
        base.blocker_lemmas = dedupe_moves(base.blocker_lemmas)
        base.validator_lemmas = dedupe_moves(base.validator_lemmas)
        base.candidate_moves = dedupe_moves(base.candidate_moves or (base.bridge_lemmas + base.blocker_lemmas + base.validator_lemmas))

        if notes:
            base.failure_analysis = (base.failure_analysis + "\n" + "\n".join(notes)).strip()
        return base
