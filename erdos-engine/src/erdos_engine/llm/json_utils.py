"""Strict JSON parsing helpers for LLM outputs."""

from __future__ import annotations

import json
import re
from typing import Callable

from pydantic import ValidationError

from erdos_engine.models import ProofMove, RLMOutput


def parse_json_with_single_repair(
    raw: str,
    repair_fn: Callable[[str], str],
) -> dict:
    """Parse raw JSON; attempt one repair pass on failure."""
    text = (raw or "").strip()
    if not text:
        return {}

    def _first_json_like_block(s: str) -> str:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", s, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            return fenced.group(1)
        # LLMs sometimes emit prose/math first (e.g. p_{n+1}) before the JSON object.
        # Scan for a balanced JSON candidate instead of slicing from the first brace.
        decoder = json.JSONDecoder()
        candidates: list[dict] = []
        for match in re.finditer(r"[\{\[]", s):
            try:
                obj, _ = decoder.raw_decode(s[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                if "moves" in obj:
                    return json.dumps(obj)
                candidates.append(obj)
            elif isinstance(obj, list):
                return json.dumps(obj)
        if candidates:
            return json.dumps(candidates[-1])
        return s

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return json.loads(_first_json_like_block(text))
        except json.JSONDecodeError:
            repaired = (repair_fn(text) or "").strip()
            if not repaired:
                return {}
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                return json.loads(_first_json_like_block(repaired))


def parse_moves_payload(
    payload: dict | list,
    source: str = "llm",
    *,
    strict: bool = False,
) -> list[ProofMove]:
    """Parse move payload to validated ProofMove list."""
    if isinstance(payload, list):
        raw_moves = payload
    elif isinstance(payload, dict):
        raw_moves = payload.get("moves", [])
    else:
        raw_moves = []
    parsed: list[ProofMove] = []
    parse_errors: list[str] = []
    for idx, entry in enumerate(raw_moves):
        if not isinstance(entry, dict):
            parse_errors.append(f"entry_{idx}:not_object")
            continue
        try:
            parsed.append(
                ProofMove(
                    id=entry.get("id") or f"move_{source}_{idx}",
                    move_type=entry["move_type"],
                    claim=entry["claim"],
                    rationale=entry.get("rationale", ""),
                    test_plan=entry.get("test_plan"),
                    dependencies=entry.get("dependencies", []),
                    expected_effect=entry.get("expected_effect", ""),
                    risk=entry.get("risk"),
                    source=source,
                    matched_prior_case_ids=entry.get("matched_prior_case_ids", []),
                    why_this_applies_here=entry.get("why_this_applies_here", ""),
                    required_preconditions=entry.get("required_preconditions", []),
                    how_to_falsify_fast=entry.get("how_to_falsify_fast", ""),
                    target_milestone=entry.get("target_milestone"),
                    theorem_chain_ids=entry.get("theorem_chain_ids", []),
                    lean_obligations=entry.get("lean_obligations", []),
                    source_quality=entry.get("source_quality", "unknown"),
                    exact_asymptotic_form=entry.get("exact_asymptotic_form"),
                    translation_steps=entry.get("translation_steps", []),
                    mechanism_core_construction=entry.get("mechanism_core_construction", ""),
                    mechanism_asymptotic_regime=entry.get("mechanism_asymptotic_regime", ""),
                    mechanism_bottleneck_attacked=entry.get("mechanism_bottleneck_attacked", ""),
                    progress_certificates=entry.get("progress_certificates", []),
                )
            )
        except (KeyError, ValidationError) as exc:
            parse_errors.append(f"entry_{idx}:{exc}")
            continue
    if strict and (parse_errors or not parsed):
        raise ValueError("strict_move_parse_failed: " + "; ".join(parse_errors or ["no_valid_moves"]))
    return parsed


def parse_rlm_payload(payload: dict | list) -> RLMOutput:
    """Parse recursive research JSON payload."""
    if isinstance(payload, list):
        # Some providers return a top-level JSON array after repair/extraction.
        # Treat it as candidate moves directly.
        candidate = parse_moves_payload(payload, source="rlm")
        return RLMOutput(candidate_moves=candidate)
    if not isinstance(payload, dict):
        return RLMOutput()
    candidate_moves = parse_moves_payload({"moves": payload.get("candidate_moves", [])}, source="rlm")
    bridge = parse_moves_payload({"moves": payload.get("bridge_lemmas", [])}, source="rlm")
    blocker = parse_moves_payload({"moves": payload.get("blocker_lemmas", [])}, source="rlm")
    validator = parse_moves_payload({"moves": payload.get("validator_lemmas", [])}, source="rlm")

    # If explicit candidate_moves missing, concatenate ranked lemma buckets.
    if not candidate_moves:
        candidate_moves = bridge + blocker + validator

    return RLMOutput(
        failure_analysis=payload.get("failure_analysis", ""),
        reformulations=payload.get("reformulations", []),
        subproblems=payload.get("subproblems", []),
        candidate_moves=candidate_moves,
        recommended_next_search_bias=payload.get("recommended_next_search_bias", ""),
        bridge_lemmas=bridge,
        blocker_lemmas=blocker,
        validator_lemmas=validator,
    )
