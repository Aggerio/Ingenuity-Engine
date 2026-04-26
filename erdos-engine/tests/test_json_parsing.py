import json

import pytest

from erdos_engine.llm.json_utils import parse_json_with_single_repair, parse_moves_payload


def test_parse_valid_llm_json() -> None:
    raw = json.dumps({"moves": [{"move_type": "construction", "claim": "c", "rationale": "r", "test_plan": None, "dependencies": [], "expected_effect": "e", "risk": None}]})
    payload = parse_json_with_single_repair(raw, lambda _: raw)
    moves = parse_moves_payload(payload)
    assert len(moves) == 1


def test_reject_invalid_llm_json_after_bad_repair() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_json_with_single_repair("{bad", lambda _: "still bad")


def test_repair_invalid_json() -> None:
    fixed = '{"moves": []}'
    payload = parse_json_with_single_repair("{bad", lambda _: fixed)
    assert payload["moves"] == []


def test_strict_move_parse_rejects_invalid_entries() -> None:
    payload = {"moves": [{"claim": "missing move_type"}]}
    with pytest.raises(ValueError):
        parse_moves_payload(payload, strict=True)
