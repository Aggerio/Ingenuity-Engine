from pathlib import Path

from erdos_engine.models import Problem, ResearchState
from erdos_engine.reporting.markdown import latest_report_for_problem, write_run_report


def test_markdown_report_generated(tmp_path: Path) -> None:
    p = Problem(
        id="sample_solved_001",
        title="Infinitely many primes",
        statement="Prove infinitely many primes.",
        tags=["number_theory"],
        status="solved",
        known_solution_path=None,
        source_url=None,
        difficulty_guess=None,
        computationally_testable=True,
        formalizable=True,
    )
    s = ResearchState(id="s", problem_id=p.id, accepted_claims=["claim"], trace=["step"])
    md, js = write_run_report(
        reports_dir=tmp_path,
        problem=p,
        config={"beam_width": 1, "max_depth": 1, "moves_per_state": 1, "use_rlm": False},
        best_state=s,
        final_status="plausible_progress",
        rlm_notes={},
        lean_preflight={"ok": True},
    )
    assert Path(md).exists()
    assert Path(js).exists()
    assert latest_report_for_problem(tmp_path, "sample_solved_001") is not None
