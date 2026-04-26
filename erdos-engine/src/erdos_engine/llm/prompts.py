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
- source_quality
- exact_asymptotic_form
- translation_steps
- mechanism_core_construction
- mechanism_asymptotic_regime
- mechanism_bottleneck_attacked
- lean_obligations
- progress_certificates

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
- `external_theorem_anchor` moves must include non-empty `translation_steps`,
  at least one nontrivial `lean_obligations` entry, and `exact_asymptotic_form`.
- `progress_certificates` must use machine-checkable types:
  `new_inequality`, `new_parameter_relation`, or `improved_coverage_bound`.
- CRITICAL JSON CONTRACT:
  - `moves` must be a JSON array of OBJECTS only.
  - Do NOT output strings/numbers/arrays inside `moves`.
  - Do NOT output markdown, prose, comments, or trailing text.
  - Missing required fields is invalid; use empty lists/strings only where schema allows.

Allowed output shape:
{{
  "moves": [
    {{
      "id": "move_0",
      "move_type": "reduction",
      "claim": "...",
      "rationale": "...",
      "test_plan": "...",
      "dependencies": ["..."],
      "expected_effect": "...",
      "risk": "medium",
      "matched_prior_case_ids": [],
      "why_this_applies_here": "...",
      "required_preconditions": [],
      "how_to_falsify_fast": "...",
      "target_milestone": "reduction_interval_to_gap",
      "theorem_chain_ids": [],
      "lean_obligations": [{{"statement": "A = B -> C = A -> C = B"}}],
      "source_quality": "medium",
      "exact_asymptotic_form": "log_2(n) <= log_2(n) + 1",
      "translation_steps": ["..."],
      "mechanism_core_construction": "...",
      "mechanism_asymptotic_regime": "iterated_logs",
      "mechanism_bottleneck_attacked": "...",
      "progress_certificates": [{{"type": "new_inequality", "statement": "..."}}]
    }}
  ]
}}

Invalid examples (never do this):
- {{"moves": ["move 1: ...", "move 2: ..."]}}
- {{"moves": [{{...}}]}} plus any text before/after JSON
- ```json ... ```

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
    search_signals: dict | None = None,
) -> str:
    states = [s.model_dump() for s in beam_states]
    signals_block = ""
    if search_signals:
        signals_block = f"""
Latest stall signals (current run snapshot — ground your analysis in THIS JSON; do not ignore it):
{json.dumps(search_signals, ensure_ascii=False)}

Additional requirements tied to the signals:
- Name concrete failure modes visible in the snapshot (e.g. Lean timeouts, tautological Lean mappings,
  score collapse, repeated fallback move IDs) and explain how your lemmas address each.
- If theorem_graph_file_stats shows on-disk graph data but the beam still lacks compositional progress,
  propose moves that reference explicit proof obligations or multi-step chains, not generic boilerplate.
"""
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
{signals_block}
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
        "Do not include explanatory text. "
        "Top-level must be a JSON object matching the schema hint. "
        "If a key expects an array of objects, do not return array entries as strings. "
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
