import json
from pathlib import Path

from erdos_engine.analysis import analyze_path_sanity, latest_attempt_dir_for_problem


def test_latest_attempt_dir_for_problem(tmp_path: Path) -> None:
    root = tmp_path / "attempts_erdos"
    (root / "erdos_004" / "20250101_000000_a").mkdir(parents=True)
    (root / "erdos_004" / "20250101_000001_b").mkdir(parents=True)
    latest = latest_attempt_dir_for_problem(root, "erdos_004")
    assert latest is not None
    assert latest.name == "20250101_000001_b"


def test_analyze_path_sanity(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt_1"
    attempt.mkdir()
    events = [
        {
            "event_type": "move_proposed",
            "payload": {
                "move": {
                    "claim": "Use Chinese remainder theorem with pairwise coprime moduli to cover interval",
                    "rationale": "CRT covering",
                    "test_plan": "construct congruence classes",
                }
            },
        },
        {
            "event_type": "move_proposed",
            "payload": {
                "move": {
                    "claim": "reduce interval with no primes to p_{n+1}-p_n bound via n = pi(N)",
                    "rationale": "prime number theorem asymptotic bridge",
                    "test_plan": "derive log n relation",
                }
            },
        },
        {
            "event_type": "move_evaluated",
            "payload": {
                "rejection_reason_category": "none",
                "checker_disagreement_summary": {"has_disagreement": False},
            },
        },
    ]
    (attempt / "events.jsonl").write_text(
        "\n".join(json.dumps(row) for row in events) + "\n",
        encoding="utf-8",
    )

    out = analyze_path_sanity(attempt, "erdos_004")
    assert out["problem_id"] == "erdos_004"
    assert out["milestone_coverage"] > 0.5
    assert isinstance(out["on_correct_path"], bool)
    assert (attempt / "path_sanity.json").exists()

