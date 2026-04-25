import json
from pathlib import Path

from erdos_engine.models import MoveEvaluation, Problem, ProofMove, RLMOutput
from erdos_engine.retrieval.hybrid import HybridRetriever
from erdos_engine.search.beam import BeamSearchConfig, BeamSearchSolver
from erdos_engine.store.failure_store import FailureStore
from erdos_engine.store.lemma_store import LemmaStore


class DummyLLM:
    def generate_moves(self, prompt: str, n: int):
        return [
            ProofMove(
                id="m",
                move_type="reduction",
                claim="test claim",
                rationale="r",
                test_plan="finite enumerate",
                dependencies=[],
                expected_effect="reduce",
                risk=None,
                source="llm",
            )
        ]

    def generate_rlm(self, prompt: str):
        return RLMOutput(
            failure_analysis="stalled",
            reformulations=["r"],
            subproblems=["s"],
            candidate_moves=[
                ProofMove(
                    id="rlm",
                    move_type="reformulation",
                    claim="rlm claim",
                    rationale="",
                    test_plan="finite",
                    dependencies=[],
                    expected_effect="reduce",
                    risk=None,
                    source="rlm",
                )
            ],
            recommended_next_search_bias="bias",
        )

    def critic_review(self, prompt: str):
        return {"ok": True}


class DummyLean:
    def evaluate(self, problem, state, move):
        return MoveEvaluation(
            move_id=move.id,
            status="unsupported",
            score_delta=-1.0,
            reason="mock",
            evidence={"lean_formalization_attempted": True, "lean_artifact_path": "x"},
        )


class DummyLeanPlausible:
    def evaluate(self, problem, state, move):
        return MoveEvaluation(
            move_id=move.id,
            status="plausible_informal",
            score_delta=0.0,
            reason="mock plausible",
            evidence={"lean_formalization_attempted": True, "lean_artifact_path": "x"},
        )


def test_beam_search_runs_without_crash(tmp_path: Path) -> None:
    data_dir = Path("data")
    reports_dir = tmp_path / "reports"
    attempts_root = tmp_path / "attempts_erdos"
    solver = BeamSearchSolver(
        llm=DummyLLM(),
        retriever=HybridRetriever(lemma_store=LemmaStore(data_dir), failure_store=FailureStore(data_dir)),
        failure_store=FailureStore(data_dir),
        lean_checker=DummyLean(),
        reports_dir=reports_dir,
        attempts_root=attempts_root,
        config=BeamSearchConfig(max_depth=2, beam_width=2, moves_per_state=1, stall_threshold=1, use_rlm=True),
    )
    problem = Problem(
        id="pid",
        title="t",
        statement="some statement",
        tags=[],
        status="solved",
        known_solution_path=None,
        source_url=None,
        difficulty_guess=None,
        computationally_testable=True,
        formalizable=True,
    )
    result = solver.solve(
        problem,
        run_config={"beam_width": 2, "max_depth": 2, "moves_per_state": 1, "use_rlm": True},
        lean_preflight={"ok": True},
    )
    assert result.problem_id == "pid"
    assert Path(result.report_path).exists()
    assert result.attempt_dir is not None
    assert Path(result.attempt_dir, "events.jsonl").exists()


def test_rlm_harness_triggers_after_stall(tmp_path: Path) -> None:
    data_dir = Path("data")
    reports_dir = tmp_path / "reports"
    attempts_root = tmp_path / "attempts_erdos"
    solver = BeamSearchSolver(
        llm=DummyLLM(),
        retriever=HybridRetriever(lemma_store=LemmaStore(data_dir), failure_store=FailureStore(data_dir)),
        failure_store=FailureStore(data_dir),
        lean_checker=DummyLean(),
        reports_dir=reports_dir,
        attempts_root=attempts_root,
        config=BeamSearchConfig(max_depth=2, beam_width=2, moves_per_state=1, stall_threshold=1, use_rlm=True),
    )
    problem = Problem(
        id="pid2",
        title="t",
        statement="some statement",
        tags=[],
        status="solved",
        known_solution_path=None,
        source_url=None,
        difficulty_guess=None,
        computationally_testable=True,
        formalizable=True,
    )
    result = solver.solve(
        problem,
        run_config={"beam_width": 2, "max_depth": 2, "moves_per_state": 1, "use_rlm": True},
        lean_preflight={"ok": True},
    )
    events = Path(result.attempt_dir or "", "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line).get("event_type") == "rlm_started" for line in events)


def test_repeated_unverified_move_does_not_keep_inflating_score(tmp_path: Path) -> None:
    data_dir = Path("data")
    reports_dir = tmp_path / "reports"
    attempts_root = tmp_path / "attempts_erdos"
    solver = BeamSearchSolver(
        llm=DummyLLM(),
        retriever=HybridRetriever(lemma_store=LemmaStore(data_dir), failure_store=FailureStore(data_dir)),
        failure_store=FailureStore(data_dir),
        lean_checker=DummyLeanPlausible(),
        reports_dir=reports_dir,
        attempts_root=attempts_root,
        config=BeamSearchConfig(max_depth=3, beam_width=1, moves_per_state=1, stall_threshold=2, use_rlm=False),
    )
    problem = Problem(
        id="erdos_004",
        title="t",
        statement="some prime statement",
        tags=[],
        status="solved",
        known_solution_path=None,
        source_url=None,
        difficulty_guess=None,
        computationally_testable=True,
        formalizable=True,
    )
    result = solver.solve(
        problem,
        run_config={"beam_width": 1, "max_depth": 3, "moves_per_state": 1, "use_rlm": False},
        lean_preflight={"ok": True},
    )
    events = [json.loads(line) for line in Path(result.attempt_dir or "", "events.jsonl").read_text(encoding="utf-8").splitlines()]
    scores = [
        float(evt["payload"]["score"])
        for evt in events
        if evt.get("event_type") == "move_evaluated" and "score" in evt.get("payload", {})
    ]
    assert scores
    if len(scores) >= 2:
        assert scores[-1] <= scores[0]
