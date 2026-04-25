"""Prompt templates for proposer, critic, and recursive research mode."""

from __future__ import annotations

import json

from erdos_engine.models import Problem, ResearchState, RetrievedItem


def _dump_items(items: list[RetrievedItem]) -> str:
    return json.dumps([item.model_dump() for item in items], ensure_ascii=False)


def build_proposer_prompt(
    problem: Problem,
    state: ResearchState,
    retrieved: list[RetrievedItem],
    failed_attempts: list[dict],
    solved_cases: list[dict],
    n: int,
) -> str:
    return f"""
You are a mathematical research assistant inside a proof-search harness.

You are NOT allowed to claim a proof is complete unless the checker verifies it.
Use case-based reasoning: reuse proven patterns only when preconditions match.

Given:
- problem statement
- current subgoals
- accepted claims
- rejected claims
- failed attempts
- retrieved lemmas/proof moves
- similar solved cases with steps and why they worked

Generate exactly {n} candidate moves.

Each move MUST be JSON with:
- move_type
- claim
- rationale
- test_plan
- dependencies
- expected_effect
- risk
- matched_prior_case_ids
- why_this_applies_here
- required_preconditions
- how_to_falsify_fast
- target_milestone

Valid target_milestone values:
- reduction_interval_to_gap
- crt_covering
- asymptotic_bridge
- validation_or_refutation

Rules:
- Be precise and falsifiable.
- Do not repeat rejected or near-duplicate moves.
- Explain transfer from solved cases explicitly.
- If preconditions are uncertain, say so and add fast falsification plan.

Problem:
{problem.statement}

State:
{substate_json(state)}

Retrieved:
{_dump_items(retrieved)}

Similar solved cases:
{json.dumps(solved_cases, ensure_ascii=False)}

Failed attempts:
{json.dumps(failed_attempts, ensure_ascii=False)}

Return only valid JSON:
{{
  "moves": [...]
}}
""".strip()


def build_rlm_prompt(
    problem: Problem,
    beam_states: list[ResearchState],
    failures: list[dict],
    solved_cases: list[dict],
) -> str:
    states = [s.model_dump() for s in beam_states]
    return f"""
You are in recursive research mode because direct beam search has stalled.

Your job:
1. Analyze why previous attempts failed.
2. Propose reformulations.
3. Generate better lemmas in three buckets:
   - bridge_lemmas (connect current state to milestone)
   - blocker_lemmas (remove immediate blockers)
   - validator_lemmas (fastly falsify tempting wrong paths)
4. Output ranked candidate moves for injection.

Each lemma/move must include:
- move_type, claim, rationale, test_plan, dependencies, expected_effect, risk
- matched_prior_case_ids
- why_this_applies_here
- required_preconditions
- how_to_falsify_fast
- target_milestone

Problem:
{problem.statement}

Beam states:
{json.dumps(states, ensure_ascii=False)}

Failures:
{json.dumps(failures, ensure_ascii=False)}

Similar solved cases:
{json.dumps(solved_cases, ensure_ascii=False)}

Return only valid JSON:
{{
  "failure_analysis": "...",
  "reformulations": [...],
  "subproblems": [...],
  "bridge_lemmas": [...],
  "blocker_lemmas": [...],
  "validator_lemmas": [...],
  "candidate_moves": [...],
  "recommended_next_search_bias": "..."
}}
""".strip()


def build_critic_prompt(problem: Problem, state: ResearchState, moves_json: list[dict]) -> str:
    return f"""
You are a skeptical mathematical critic.
Given candidate moves, identify:
- vague claims
- likely false claims
- missing assumptions
- possible counterexamples
- whether transfer from solved cases is valid
- whether required preconditions are actually satisfied
- whether "why this applies" is causal or handwavy
- whether each move is testable fast

Problem:
{problem.statement}

State:
{substate_json(state)}

Moves:
{json.dumps(moves_json, ensure_ascii=False)}

Return only valid JSON object.
""".strip()


def build_json_repair_prompt(bad_text: str, schema_hint: str) -> str:
    return (
        "Return valid JSON only. "
        "Do not add markdown fences. "
        f"Schema hint: {schema_hint}. "
        f"Input: {bad_text}"
    )


def substate_json(state: ResearchState) -> str:
    return json.dumps(
        {
            "subgoals": state.subgoals,
            "accepted_claims": state.accepted_claims,
            "rejected_claims": state.rejected_claims,
            "assumptions": state.assumptions,
        },
        ensure_ascii=False,
    )
