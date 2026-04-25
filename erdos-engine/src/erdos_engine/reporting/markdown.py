"""Markdown and JSON report generation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from erdos_engine.models import Problem, ResearchState, RunSession


def _table_row(values: list[str]) -> str:
    return "| " + " | ".join(v.replace("\n", " ") for v in values) + " |"


def _render_report_lines(
    problem: Problem,
    config: dict,
    best_state: ResearchState,
    final_status: str,
    rlm_notes: dict,
    lean_preflight: dict,
) -> list[str]:
    accepted = [
        ev
        for ev in best_state.evaluations
        if ev.status in {"verified_formally", "accepted_computationally", "plausible_informal"}
    ]
    rejected = [ev for ev in best_state.evaluations if ev.status == "rejected_by_counterexample"]
    move_map = {m.id: m for m in best_state.moves}

    lines = [
        f"# Run Report: {problem.title}",
        "",
        "## Problem",
        problem.statement,
        "",
        "## Configuration",
        f"- beam_width: {config.get('beam_width')}",
        f"- max_depth: {config.get('max_depth')}",
        f"- moves_per_state: {config.get('moves_per_state')}",
        f"- use_rlm: {config.get('use_rlm')}",
        "",
        "## Final Status",
        final_status,
        "",
        "## Lean Preflight Status",
        json.dumps(lean_preflight, indent=2),
        "",
        "## Best State Summary",
        f"- score: {best_state.score}",
        f"- depth: {best_state.depth}",
        f"- subgoals: {best_state.subgoals}",
        f"- accepted claims: {best_state.accepted_claims}",
        "",
        "## Candidate Proof Skeleton",
    ]

    for i, claim in enumerate(best_state.accepted_claims or ["No accepted claims"], start=1):
        lines.append(f"{i}. {claim}")

    lines += [
        "",
        "## Formal Verification Summary",
        f"- target theorem status: {final_status}",
        f"- verified intermediate lemmas: {[e.move_id for e in accepted if e.status == 'verified_formally']}",
        f"- failed formalizations: {[e.move_id for e in rejected]}",
        "",
        "## Accepted / Useful Moves",
        _table_row(["move_type", "claim", "status", "score_delta", "evidence"]),
        _table_row(["---", "---", "---", "---", "---"]),
    ]

    for ev in accepted:
        move = move_map.get(ev.move_id)
        lines.append(
            _table_row(
                [
                    move.move_type if move else "unknown",
                    move.claim if move else ev.move_id,
                    ev.status,
                    str(ev.score_delta),
                    json.dumps(ev.evidence, ensure_ascii=False)[:120],
                ]
            )
        )

    lines += [
        "",
        "## Rejected Moves",
        _table_row(["claim", "reason", "counterexample"]),
        _table_row(["---", "---", "---"]),
    ]
    for ev in rejected:
        move = move_map.get(ev.move_id)
        lines.append(_table_row([move.claim if move else ev.move_id, ev.reason, ev.counterexample or ""]))

    lines += ["", "## Retrieved Lemmas"]
    for item in best_state.retrieved_lemmas:
        lines.append(f"- {item}")

    lines += [
        "",
        "## RLM Research Findings",
        f"- failure_analysis: {rlm_notes.get('failure_analysis', '')}",
        f"- reformulations: {rlm_notes.get('reformulations', [])}",
        f"- subproblems: {rlm_notes.get('subproblems', [])}",
        f"- recommended_next_search_bias: {rlm_notes.get('recommended_next_search_bias', '')}",
        "",
        "## Trace",
    ]
    for t in best_state.trace:
        lines.append(f"- {t}")

    return lines


def write_run_report_from_session(
    session: RunSession,
    problem: Problem,
    best_state: ResearchState,
    final_status: str,
    rlm_notes: dict,
) -> tuple[str, str]:
    """Write markdown/json report using run session artifact locations."""
    md_path = Path(session.artifacts.report_md_path)
    json_path = Path(session.artifacts.report_json_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    lines = _render_report_lines(
        problem=problem,
        config=session.config,
        best_state=best_state,
        final_status=final_status,
        rlm_notes=rlm_notes,
        lean_preflight=session.lean_preflight,
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "run_id": session.run_id,
        "problem": problem.model_dump(),
        "config": session.config,
        "final_status": final_status,
        "best_state": best_state.model_dump(),
        "rlm_notes": rlm_notes,
        "lean_preflight": session.lean_preflight,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(md_path), str(json_path)


def write_run_report(
    reports_dir: Path,
    problem: Problem,
    config: dict,
    best_state: ResearchState,
    final_status: str,
    rlm_notes: dict,
    lean_preflight: dict,
) -> tuple[str, str]:
    """Compatibility wrapper for legacy report path contract."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{problem.id}"
    md_path = reports_dir / f"{run_id}.md"
    json_path = reports_dir / f"{run_id}.json"

    lines = _render_report_lines(problem, config, best_state, final_status, rlm_notes, lean_preflight)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "problem": problem.model_dump(),
        "config": config,
        "final_status": final_status,
        "best_state": best_state.model_dump(),
        "rlm_notes": rlm_notes,
        "lean_preflight": lean_preflight,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(md_path), str(json_path)


def latest_report_for_problem(reports_dir: Path, problem_id: str) -> Path | None:
    """Return latest markdown report for a problem id."""
    matches = sorted(reports_dir.glob(f"*_{problem_id}.md"))
    return matches[-1] if matches else None
