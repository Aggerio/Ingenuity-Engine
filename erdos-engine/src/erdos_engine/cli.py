"""Command-line interface for Erdos Engine."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from erdos_engine.analysis import analyze_path_sanity, latest_attempt_dir_for_problem
from erdos_engine.checkers.lean import LeanChecker, LeanPreflightError
from erdos_engine.config import Settings
from erdos_engine.ingestion import bootstrap_from_previous_info, bootstrap_theorem_graph, import_erdos_problem
from erdos_engine.llm.mock import MockLLMClient
from erdos_engine.llm.openai_compatible import OpenAICompatibleLLMClient
from erdos_engine.logging_utils import configure_logging
from erdos_engine.models import Lemma, ProofMove
from erdos_engine.reporting.markdown import latest_report_for_problem
from erdos_engine.retrieval.hybrid import HybridRetriever
from erdos_engine.search.beam import BeamSearchConfig, BeamSearchSolver
from erdos_engine.store.failure_store import FailureStore
from erdos_engine.store.lemma_store import LemmaStore
from erdos_engine.store.problem_store import ProblemStore
from erdos_engine.store.theorem_graph_store import TheoremGraphStore

LOG = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="erdos-engine")
    parser.add_argument("--debug", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-problems")

    show = sub.add_parser("show-problem")
    show.add_argument("problem_id")

    run = sub.add_parser("run")
    run.add_argument("problem_id")
    run.add_argument("--beam-width", type=int, default=None)
    run.add_argument("--max-depth", type=int, default=None)
    run.add_argument("--moves-per-state", type=int, default=None)
    run.add_argument("--retrieved-lemmas-per-state", type=int, default=None)
    run.add_argument("--stall-threshold", type=int, default=None)
    run.add_argument("--lean-timeout-seconds", type=int, default=None)
    run.add_argument("--use-rlm", action="store_true", default=None)
    run.add_argument("--no-use-rlm", action="store_false", dest="use_rlm")
    run.add_argument("--use-critic", action="store_true", default=None)
    run.add_argument("--no-use-critic", action="store_false", dest="use_critic")
    run.add_argument("--use-secondary-checkers", action="store_true", default=None)
    run.add_argument("--no-use-secondary-checkers", action="store_false", dest="use_secondary_checkers")
    run.add_argument("--attempts-root", type=str, default=None)
    run.add_argument("--run-label", type=str, default=None)
    run.add_argument("--llm-timeout-seconds", type=int, default=None)
    run.add_argument("--llm-max-tokens", type=int, default=None)

    add_lemma = sub.add_parser("add-lemma")
    add_lemma.add_argument("--file", required=True)

    report = sub.add_parser("report")
    report.add_argument("run_id")

    import_problem = sub.add_parser("import-erdos-problem")
    import_problem.add_argument("number", type=int)

    bootstrap = sub.add_parser("bootstrap-knowledge")
    bootstrap.add_argument("--from", dest="source_root", required=True)

    sanity = sub.add_parser("sanity-check-path")
    sanity.add_argument("problem_id")
    sanity.add_argument("--attempt-dir", type=str, default=None)
    sanity.add_argument("--attempts-root", type=str, default=None)

    sub.add_parser("init-sample-data")
    return parser


def _select_llm(settings: Settings):
    if settings.openai_compatible_api_key:
        proposer = OpenAICompatibleLLMClient(
            api_key=settings.openai_compatible_api_key,
            base_url=settings.openai_compatible_base_url,
            model=settings.openai_compatible_model,
            timeout=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )
        critic = None
        if settings.openai_compatible_critic_model:
            critic = OpenAICompatibleLLMClient(
                api_key=settings.openai_compatible_critic_api_key
                or settings.openai_compatible_api_key,
                base_url=settings.openai_compatible_critic_base_url
                or settings.openai_compatible_base_url,
                model=settings.openai_compatible_critic_model,
                timeout=settings.llm_timeout_seconds,
                max_tokens=settings.llm_max_tokens,
            )
        return proposer, critic
    LOG.info("No OPENAI_COMPATIBLE_API_KEY found; using MockLLMClient")
    mock = MockLLMClient(seed=settings.random_seed)
    return mock, None


def _resolve_paths(settings: Settings) -> tuple[Path, Path, Path]:
    cwd = Path.cwd()
    data_dir = (cwd / settings.data_dir).resolve()
    reports_dir = (cwd / settings.reports_dir).resolve()
    lean_dir = (cwd / settings.lean_project_dir).resolve()
    return data_dir, reports_dir, lean_dir


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    configure_logging(debug=args.debug)

    settings = Settings.from_env()
    data_dir, reports_dir, lean_dir = _resolve_paths(settings)

    problem_store = ProblemStore(data_dir)
    lemma_store = LemmaStore(data_dir)
    failure_store = FailureStore(data_dir)
    theorem_graph_store = TheoremGraphStore(data_dir)

    if args.command == "init-sample-data":
        problem_store.init_sample_data(force=False)
        print("Sample data verified in data/problems and data/lemma_db")
        return 0

    if args.command == "list-problems":
        for p in problem_store.list_problems():
            print(f"{p.id}\t{p.status}\t{p.title}")
        return 0

    if args.command == "show-problem":
        p = problem_store.get_problem(args.problem_id)
        print(f"id: {p.id}")
        print(f"title: {p.title}")
        print(f"status: {p.status}")
        print(f"tags: {', '.join(p.tags)}")
        print("statement:")
        print(p.statement)
        return 0

    if args.command == "add-lemma":
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        if "move_type" in payload:
            lemma_store.add_proof_move(ProofMove(**payload))
            print("Added proof move")
        else:
            lemma_store.add_lemma(Lemma(**payload))
            print("Added lemma")
        return 0

    if args.command == "import-erdos-problem":
        problem_id = import_erdos_problem(number=args.number, data_dir=data_dir)
        print(problem_id)
        return 0

    if args.command == "bootstrap-knowledge":
        result = bootstrap_from_previous_info(Path(args.source_root), lemma_store)
        graph_result = bootstrap_theorem_graph(lemma_store, theorem_graph_store)
        print(json.dumps({**result, "theorem_graph": graph_result}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "sanity-check-path":
        attempts_root = (
            Path(args.attempts_root).resolve()
            if args.attempts_root
            else (Path.cwd() / ".." / "attempts_erdos").resolve()
        )
        attempt_dir = Path(args.attempt_dir).resolve() if args.attempt_dir else None
        if attempt_dir is None:
            found = latest_attempt_dir_for_problem(attempts_root, args.problem_id)
            if found is None:
                print(f"No attempt directories found for {args.problem_id} in {attempts_root}")
                return 1
            attempt_dir = found
        result = analyze_path_sanity(attempt_dir=attempt_dir, problem_id=args.problem_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "report":
        report_path = latest_report_for_problem(reports_dir, args.run_id)
        if not report_path:
            print(f"No report found for problem id: {args.run_id}")
            return 1
        print(str(report_path))
        return 0

    if args.command == "run":
        problem = problem_store.get_problem(args.problem_id)
        if not theorem_graph_store.load_nodes():
            bootstrap_theorem_graph(lemma_store, theorem_graph_store)
        run_settings = settings.with_overrides(
            beam_width=args.beam_width,
            max_depth=args.max_depth,
            moves_per_state=args.moves_per_state,
            retrieved_lemmas_per_state=args.retrieved_lemmas_per_state,
            stall_threshold=args.stall_threshold,
            lean_timeout_seconds=args.lean_timeout_seconds,
            use_rlm=args.use_rlm,
            use_critic=args.use_critic,
            use_secondary_checkers=args.use_secondary_checkers,
            llm_timeout_seconds=args.llm_timeout_seconds,
            llm_max_tokens=args.llm_max_tokens,
        )

        attempts_root = (
            Path(args.attempts_root).resolve()
            if args.attempts_root
            else (Path.cwd() / ".." / "attempts_erdos").resolve()
        )

        lean_checker = LeanChecker(
            project_dir=lean_dir,
            timeout_seconds=run_settings.lean_timeout_seconds,
        )
        if run_settings.lean_required:
            try:
                lean_preflight = lean_checker.preflight()
            except LeanPreflightError as exc:
                print(f"Lean preflight failed: {exc}")
                return 2
        else:
            lean_preflight = {"status": "disabled"}

        llm, critic_llm = _select_llm(run_settings)
        retriever = HybridRetriever(
            lemma_store=lemma_store,
            failure_store=failure_store,
            theorem_graph_store=theorem_graph_store,
        )
        solver = BeamSearchSolver(
            llm=llm,
            critic_llm=critic_llm,
            retriever=retriever,
            failure_store=failure_store,
            lean_checker=lean_checker,
            reports_dir=reports_dir,
            attempts_root=attempts_root,
            problem_store=problem_store,
            theorem_graph_store=theorem_graph_store,
            config=BeamSearchConfig(
                beam_width=run_settings.beam_width,
                max_depth=run_settings.max_depth,
                moves_per_state=run_settings.moves_per_state,
                retrieved_lemmas_per_state=run_settings.retrieved_lemmas_per_state,
                stall_threshold=run_settings.stall_threshold,
                use_rlm=run_settings.use_rlm,
                use_critic=run_settings.use_critic,
                use_secondary_checkers=run_settings.use_secondary_checkers,
            ),
        )
        result = solver.solve(
            problem=problem,
            run_config={
                "beam_width": run_settings.beam_width,
                "max_depth": run_settings.max_depth,
                "moves_per_state": run_settings.moves_per_state,
                "use_rlm": run_settings.use_rlm,
                "attempts_root": str(attempts_root),
                "run_label": args.run_label,
            },
            lean_preflight=lean_preflight,
        )
        print(result.summary)
        print(result.attempt_dir or "")
        print(result.report_path)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
