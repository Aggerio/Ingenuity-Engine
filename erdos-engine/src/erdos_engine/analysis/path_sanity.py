"""Sanity checks for whether a run followed the right proof trajectory."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def latest_attempt_dir_for_problem(attempts_root: Path, problem_id: str) -> Path | None:
    """Return latest attempt directory for a problem, if present."""
    pdir = attempts_root / problem_id
    if not pdir.exists():
        return None
    runs = sorted([p for p in pdir.iterdir() if p.is_dir()])
    return runs[-1] if runs else None


def _problem4_milestones() -> dict[str, list[str]]:
    return {
        "reduction_interval_to_gap": ["interval", "contains no primes", "p_{n+1}", "pi(", "π("],
        "crt_covering": ["crt", "chinese remainder", "congruence", "pairwise coprime", "moduli"],
        "asymptotic_bridge": ["prime number theorem", "pnt", "log n", "log log n", "asymptotic"],
        "known_solution_lineage": ["erdős-rankin", "erdos-rankin", "maynard", "ford", "konyagin", "tao"],
    }


def _problem4_red_flags() -> dict[str, list[str]]:
    return {
        "bad_crt_assignment": ["prime divisor of i", "choose p_i dividing i", "reusing prime divisors"],
        "bad_asymptotic": ["log n ~ q", "log n approx q", "log n asymptotic q"],
        "domain_mistake": ["10^6", "10^7", "10^8", "10^9"],
        "irrelevant_euclid_path": ["product(primes)+1", "infinitely many primes by contradiction"],
    }


def _extract_move_text(payload: dict) -> str:
    move = payload.get("move", {})
    parts = [
        str(move.get("claim", "")),
        str(move.get("rationale", "")),
        str(move.get("test_plan", "")),
    ]
    return " ".join(parts).lower()


def analyze_path_sanity(attempt_dir: Path, problem_id: str) -> dict:
    """Analyze run event trajectory and estimate whether it followed a good path."""
    events_path = attempt_dir / "events.jsonl"
    if not events_path.exists():
        raise FileNotFoundError(f"Missing events.jsonl in {attempt_dir}")

    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    move_events = [e for e in events if e.get("event_type") == "move_proposed"]
    eval_events = [e for e in events if e.get("event_type") == "move_evaluated"]

    milestones = _problem4_milestones() if problem_id == "erdos_004" else {}
    red_flags = _problem4_red_flags() if problem_id == "erdos_004" else {}

    hit_counter: Counter[str] = Counter()
    flag_counter: Counter[str] = Counter()

    for event in move_events:
        text = _extract_move_text(event.get("payload", {}))
        for mkey, markers in milestones.items():
            if any(marker in text for marker in markers):
                hit_counter[mkey] += 1
        for fkey, markers in red_flags.items():
            if any(marker in text for marker in markers):
                if fkey == "domain_mistake":
                    if "log log log log" in text:
                        flag_counter[fkey] += 1
                else:
                    flag_counter[fkey] += 1

    rejection_categories: Counter[str] = Counter()
    disagreement_count = 0
    for event in eval_events:
        payload = event.get("payload", {})
        rejection = str(payload.get("rejection_reason_category", "none"))
        rejection_categories[rejection] += 1
        summary = payload.get("checker_disagreement_summary", {})
        if summary.get("has_disagreement"):
            disagreement_count += 1

    milestone_coverage = (
        len([k for k in milestones if hit_counter.get(k, 0) > 0]) / len(milestones)
        if milestones
        else 0.0
    )
    flag_density = (sum(flag_counter.values()) / len(move_events)) if move_events else 0.0
    disagreement_ratio = (disagreement_count / len(eval_events)) if eval_events else 0.0

    raw_score = (0.7 * milestone_coverage) - (0.8 * flag_density) - (0.2 * disagreement_ratio)
    confidence = max(0.0, min(1.0, (raw_score + 1.0) / 2.0))
    on_correct_path = confidence >= 0.55 and milestone_coverage >= 0.50 and flag_density <= 0.20

    summary = {
        "problem_id": problem_id,
        "attempt_dir": str(attempt_dir),
        "events_count": len(events),
        "move_events_count": len(move_events),
        "eval_events_count": len(eval_events),
        "milestone_hits": dict(hit_counter),
        "milestone_coverage": round(milestone_coverage, 3),
        "red_flags": dict(flag_counter),
        "flag_density": round(flag_density, 3),
        "rejection_reason_categories": dict(rejection_categories),
        "checker_disagreement_ratio": round(disagreement_ratio, 3),
        "confidence": round(confidence, 3),
        "on_correct_path": on_correct_path,
    }

    out_path = attempt_dir / "path_sanity.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary

