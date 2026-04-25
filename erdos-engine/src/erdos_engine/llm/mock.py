"""Deterministic mock LLM client for local tests and offline mode."""

from __future__ import annotations

from random import Random

from erdos_engine.llm.base import LLMClient
from erdos_engine.models import ProofMove, RLMOutput


class MockLLMClient(LLMClient):
    """Mock implementation that emits deterministic structured moves."""

    def __init__(self, seed: int = 13, emit_invalid_json: bool = False) -> None:
        self.rng = Random(seed)
        self.emit_invalid_json = emit_invalid_json

    def generate_moves(self, prompt: str, n: int) -> list[ProofMove]:
        problem_hint = "prime" if "prime" in prompt.lower() else "graph"
        out: list[ProofMove] = []
        for i in range(n):
            if problem_hint == "prime":
                claim = "If p divides product(primes)+1 then p is not in listed primes"
                move_type = "construction"
                test_plan = "modular residues for small prime lists"
            else:
                claim = "In K6 edge 2-colorings, monochromatic triangle appears"
                move_type = "brute_force_experiment"
                test_plan = "enumerate all 2-colorings of K6"
            out.append(
                ProofMove(
                    id=f"mock_{i}",
                    move_type=move_type,  # type: ignore[arg-type]
                    claim=claim,
                    rationale="Deterministic mock proposal",
                    test_plan=test_plan,
                    dependencies=[],
                    expected_effect="Adds testable direction",
                    risk="low",
                    source="llm",
                )
            )
        return out

    def generate_rlm(self, prompt: str) -> RLMOutput:
        return RLMOutput(
            failure_analysis="Search appears to repeat high-level ideas without formal assumptions.",
            reformulations=["State the claim as a contradiction with finite witness."],
            subproblems=["Formalize a supporting lemma with explicit quantifiers."],
            candidate_moves=[
                ProofMove(
                    id="rlm_0",
                    move_type="reformulation",
                    claim="Rewrite target as existence of counterexample impossible in finite bound",
                    rationale="Supports bounded search and formalization",
                    test_plan="bounded finite model check",
                    dependencies=[],
                    expected_effect="narrower subgoal",
                    risk="medium",
                    source="rlm",
                )
            ],
            recommended_next_search_bias="prefer_assumption_complete_moves",
        )

    def critic_review(self, prompt: str) -> dict:
        return {
            "vague_claims": [],
            "likely_false": [],
            "missing_assumptions": ["ensure quantifiers and domain bounds are explicit"],
            "possible_counterexamples": [],
            "testability": "moderate",
        }
