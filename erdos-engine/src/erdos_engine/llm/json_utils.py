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
        start_obj = s.find("{")
        start_arr = s.find("[")
        starts = [idx for idx in (start_obj, start_arr) if idx != -1]
        if not starts:
            return s
        start = min(starts)
        end_obj = s.rfind("}")
        end_arr = s.rfind("]")
        end = max(end_obj, end_arr)
        if end > start:
            return s[start : end + 1]
        return s[start:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return json.loads(_first_json_like_block(text))
        except json.JSONDecodeError:
            repaired = repair_fn(text)
            return json.loads(repaired)


def parse_moves_payload(payload: dict, source: str = "llm") -> list[ProofMove]:
    """Parse move payload to validated ProofMove list."""
    raw_moves = payload.get("moves", [])
    parsed: list[ProofMove] = []
    for idx, entry in enumerate(raw_moves):
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
                )
            )
        except (KeyError, ValidationError):
            continue
    return parsed


def parse_rlm_payload(payload: dict) -> RLMOutput:
    """Parse recursive research JSON payload."""
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
