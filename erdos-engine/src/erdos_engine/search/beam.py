"""Beam search solver for research-state exploration."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

from erdos_engine.checkers.algebra import AlgebraChecker
from erdos_engine.checkers.brute_force import BruteForceChecker
from erdos_engine.checkers.graph import GraphChecker
from erdos_engine.checkers.lean import LeanChecker
from erdos_engine.checkers.number_theory import NumberTheoryChecker
from erdos_engine.checkers.z3_checker import Z3Checker
from erdos_engine.harness.events import load_events
from erdos_engine.harness.reducer import reduce_run_events
from erdos_engine.harness.session import EventRecorder, RunSessionBuilder
from erdos_engine.llm.base import LLMClient
from erdos_engine.llm.prompts import build_critic_prompt, build_proposer_prompt
from erdos_engine.models import MoveEvaluation, Problem, ResearchState, RunResult
from erdos_engine.reporting.markdown import write_run_report, write_run_report_from_session
from erdos_engine.retrieval.case_based import SolvedCaseRetriever
from erdos_engine.retrieval.hybrid import HybridRetriever
from erdos_engine.rlm.harness import RLMHarness
from erdos_engine.search.scoring import score_move_evaluation, score_state
from erdos_engine.search.stall import is_semantically_stalled, is_stalled
from erdos_engine.store.failure_store import FailureStore
from erdos_engine.store.problem_store import ProblemStore

LOG = logging.getLogger(__name__)


@dataclass
class BeamSearchConfig:
    beam_width: int = 5
    max_depth: int = 5
    moves_per_state: int = 8
    retrieved_lemmas_per_state: int = 10
    stall_threshold: int = 2
    use_rlm: bool = True
    use_critic: bool = False
    use_secondary_checkers: bool = False


class BeamSearchSolver:
    """Lean-first beam search over research states."""

    def __init__(
        self,
        llm: LLMClient,
        retriever: HybridRetriever,
        failure_store: FailureStore,
        lean_checker: LeanChecker,
        reports_dir,
        attempts_root: Path,
        config: BeamSearchConfig,
        critic_llm: LLMClient | None = None,
        problem_store: ProblemStore | None = None,
    ) -> None:
        self.llm = llm
        self.critic_llm = critic_llm or llm
        self.retriever = retriever
        self.failure_store = failure_store
        self.lean_checker = lean_checker
        self.secondary_checkers = [
            NumberTheoryChecker(),
            GraphChecker(),
            AlgebraChecker(),
            BruteForceChecker(),
            Z3Checker(),
        ]
        self.config = config
        self.rlm = RLMHarness(llm)
        self.reports_dir = Path(reports_dir)
        self.attempts_root = Path(attempts_root)
        self.case_retriever = SolvedCaseRetriever(problem_store) if problem_store else None

    @staticmethod
    def _normalize_claim(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        normalized = re.sub(r"[^a-z0-9 ]", "", normalized)
        return normalized

    def _claim_fingerprint(self, text: str) -> str:
        return hashlib.sha1(self._normalize_claim(text).encode("utf-8")).hexdigest()[:16]

    def _novelty_score(self, claim: str, accepted_claims: list[str]) -> float:
        if not accepted_claims:
            return 0.2
        normalized = self._normalize_claim(claim)
        sims = [
            SequenceMatcher(None, normalized, self._normalize_claim(existing)).ratio()
            for existing in accepted_claims
        ]
        max_sim = max(sims)
        if max_sim >= 0.92:
            return 0.0
        if max_sim >= 0.80:
            return 0.03
        return 0.2

    @staticmethod
    def _problem4_milestones() -> dict[str, list[str]]:
        return {
            "reduction_gap_to_pn": ["p_{n+1}", "pi(", "π(", "reduction", "interval"],
            "crt_covering": ["crt", "chinese remainder", "congruence", "cover", "moduli"],
            "parameter_growth": ["log n", "log n ~", "asymptotic", "q", "n", "growth"],
        }

    def _milestones_hit(self, problem: Problem, move) -> list[str]:
        if problem.id != "erdos_004":
            return []
        text = " ".join([move.claim, move.rationale or "", move.test_plan or ""]).lower()
        hits: list[str] = []
        for key, markers in self._problem4_milestones().items():
            if any(marker in text for marker in markers):
                hits.append(key)
        return hits

    def _negative_memory_blocked(self, problem: Problem, move, failed_attempts: list[dict]) -> tuple[bool, str]:
        """Block near-duplicate failed directions."""
        claim = self._normalize_claim(move.claim)
        for failure in failed_attempts:
            failed_claim = self._normalize_claim(str(failure.get("move", {}).get("claim", "")))
            if not failed_claim:
                continue
            sim = SequenceMatcher(None, claim, failed_claim).ratio()
            if sim >= 0.9:
                reason = str(failure.get("reason_failed", "near-duplicate of failed attempt"))
                return True, reason
        return False, ""

    def _rlm_relevance_score(self, move, state: ResearchState, problem: Problem) -> float:
        score = 0.0
        hits = self._milestones_hit(problem, move)
        score += 2.0 * len(hits)
        score += self._novelty_score(move.claim, state.accepted_claims) * 5.0
        if move.required_preconditions:
            text = " ".join(state.assumptions + state.subgoals + state.accepted_claims).lower()
            matched = sum(1 for p in move.required_preconditions if p.lower() in text)
            score += matched
        if move.how_to_falsify_fast:
            score += 0.5
        return score

    @staticmethod
    def _checker_disagreement(lean_eval: MoveEvaluation, experiments: list[dict]) -> dict:
        statuses = [lean_eval.status]
        for exp in experiments:
            statuses.append(str(exp.get("evaluation", {}).get("status", "unknown")))
        compact = sorted(set(statuses))
        return {
            "statuses": compact,
            "has_disagreement": len(compact) > 1,
        }

    def _initial_state(self, problem: Problem) -> ResearchState:
        subgoals = [problem.statement]
        if problem.id == "erdos_004":
            subgoals = [
                "Milestone 1: reduction from prime-free interval to p_{n+1}-p_n bound",
                "Milestone 2: valid CRT covering lemma with pairwise-coprime structure",
                "Milestone 3: parameter-growth lemma linking N, Q, and n",
                problem.statement,
            ]
        return ResearchState(
            id=f"state_{uuid4().hex[:8]}",
            problem_id=problem.id,
            depth=0,
            subgoals=subgoals,
            trace=["initialized state"],
        )

    def _is_target_solved(self, problem: Problem, state: ResearchState) -> bool:
        target = problem.statement.lower().strip()
        for move, evaluation in zip(state.moves, state.evaluations):
            if evaluation.status != "verified_formally":
                continue
            if target in move.claim.lower():
                return True
        return False

    def _evaluate_move(
        self,
        problem: Problem,
        state: ResearchState,
        move,
    ) -> tuple[MoveEvaluation, list[dict]]:
        lean_eval = self.lean_checker.evaluate(problem, state, move)
        experiments: list[dict] = []
        if self.config.use_secondary_checkers:
            for checker in self.secondary_checkers:
                if not checker.supports(problem, move):
                    continue
                sub_eval = checker.evaluate(problem, state, move)
                experiments.append({"checker": checker.name, "evaluation": sub_eval.model_dump()})
        if lean_eval.status == "rejected_by_counterexample":
            self.failure_store.record_failure(
                problem_id=problem.id,
                move=move.model_dump(),
                reason_failed=lean_eval.reason,
                counterexample=lean_eval.counterexample,
                checker_output=lean_eval.evidence,
                reusable_warning="Lean rejected this formalization; check assumptions and tactic plan.",
            )
        return lean_eval, experiments

    @staticmethod
    def _broad_move_reason(problem: Problem, move) -> str | None:
        if problem.id != "erdos_004":
            return None
        claim = (move.claim or "").strip()
        rationale = (move.rationale or "").strip()
        test_plan = (move.test_plan or "").strip()
        lc = claim.lower()
        tokens = claim.split()
        generic_markers = [
            "construct",
            "reduce the target",
            "prove the statement",
            "advance milestone",
            "standard argument",
        ]
        has_math_signal = any(sym in claim for sym in ["=", ">", "<", "~", "≈", "≡", "π", "mod", "log", "^", "/"])

        if len(tokens) < 10:
            return "broad_move: claim too short"
        if not has_math_signal and any(m in lc for m in generic_markers):
            return "broad_move: generic claim without concrete math relation"
        if len(test_plan) < 24:
            return "broad_move: missing concrete test plan"
        if len((move.dependencies or [])) == 0:
            return "broad_move: missing dependencies"
        if problem.id == "erdos_004":
            required_markers = ["prime", "gap", "crt", "log", "pi", "π", "mod", "interval"]
            if not any(m in (lc + " " + rationale.lower() + " " + test_plan.lower()) for m in required_markers):
                return "broad_move: not anchored to problem-4 domain terms"
        return None

    def solve(self, problem: Problem, run_config: dict, lean_preflight: dict) -> RunResult:
        """Run beam search and return final result with persisted report."""
        session_builder = RunSessionBuilder(self.attempts_root)
        run_session = session_builder.create(
            problem_id=problem.id,
            config=run_config,
            run_label=run_config.get("run_label"),
        )
        run_session.lean_preflight = lean_preflight

        events_path = Path(run_session.artifacts.events_path)
        recorder = EventRecorder(events_path)
        recorder.emit("run_started", {"problem_id": problem.id, "config": run_config})

        lean_preflight_path = Path(run_session.artifacts.lean_preflight_path)
        lean_preflight_path.parent.mkdir(parents=True, exist_ok=True)
        lean_preflight_path.write_text(json.dumps(lean_preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        previous_debug_dir = os.environ.get("ERDOS_LLM_DEBUG_DIR")
        os.environ["ERDOS_LLM_DEBUG_DIR"] = str(lean_preflight_path.parent)

        beam: list[ResearchState] = [self._initial_state(problem)]
        best_scores: list[float] = [0.0]
        novelty_history: list[float] = []
        rlm_notes: dict = {}
        final_status = "failed"

        try:
            for depth in range(1, self.config.max_depth + 1):
                candidates: list[ResearchState] = []
                for state in beam:
                    query = " ".join(state.subgoals + state.accepted_claims + state.rejected_claims)
                    retrieved = self.retriever.retrieve(
                        query=query,
                        tags=problem.tags,
                        top_k=self.config.retrieved_lemmas_per_state,
                        problem_id=problem.id,
                    )
                    failed_attempts = self.failure_store.search_failures(problem.id, query, top_k=5)
                    recorder.emit(
                        "retrieval",
                        {
                            "query": query,
                            "retrieved_ids": [r.item_id for r in retrieved],
                            "failed_attempts": len(failed_attempts),
                        },
                        depth=depth,
                        state_id=state.id,
                    )

                    prompt = build_proposer_prompt(
                        problem=problem,
                        state=state,
                        retrieved=retrieved,
                        failed_attempts=failed_attempts,
                        solved_cases=self.case_retriever.retrieve(problem, top_k=3) if self.case_retriever else [],
                        n=self.config.moves_per_state,
                    )
                    moves = self.llm.generate_moves(prompt, self.config.moves_per_state)
                    if self.config.use_critic and moves:
                        critic_prompt = build_critic_prompt(
                            problem=problem,
                            state=state,
                            moves_json=[m.model_dump() for m in moves],
                        )
                        critique = self.critic_llm.critic_review(critic_prompt)
                        state.trace.append(f"critic: {critique}")

                    for move in moves:
                        broad_reason = self._broad_move_reason(problem, move)
                        if broad_reason:
                            recorder.emit(
                                "move_evaluated",
                                {
                                    "move": move.model_dump(),
                                    "evaluation": {
                                        "move_id": move.id,
                                        "status": "rejected_by_counterexample",
                                        "score_delta": -1.0,
                                        "reason": broad_reason,
                                        "evidence": {"rejection_category": "broad_move"},
                                        "counterexample": broad_reason,
                                    },
                                    "score": state.score - 1.0,
                                    "state": state.model_dump(),
                                    "claim_fingerprint": self._claim_fingerprint(move.claim),
                                    "rejection_reason_category": "broad_move",
                                    "checker_disagreement_summary": {"statuses": ["blocked"], "has_disagreement": False},
                                    "novelty": 0.0,
                                    "milestones_hit": [],
                                },
                                depth=depth,
                                state_id=state.id,
                            )
                            continue
                        blocked, blocked_reason = self._negative_memory_blocked(problem, move, failed_attempts)
                        if blocked:
                            recorder.emit(
                                "move_evaluated",
                                {
                                    "move": move.model_dump(),
                                    "evaluation": {
                                        "move_id": move.id,
                                        "status": "rejected_by_counterexample",
                                        "score_delta": -2.0,
                                        "reason": f"blocked_by_negative_memory: {blocked_reason}",
                                        "evidence": {"rejection_category": "negative_memory_block"},
                                        "counterexample": blocked_reason,
                                    },
                                    "score": state.score - 2.0,
                                    "state": state.model_dump(),
                                    "claim_fingerprint": self._claim_fingerprint(move.claim),
                                    "rejection_reason_category": "negative_memory_block",
                                    "checker_disagreement_summary": {"statuses": ["blocked"], "has_disagreement": False},
                                    "novelty": 0.0,
                                    "milestones_hit": [],
                                },
                                depth=depth,
                                state_id=state.id,
                            )
                            continue

                        fingerprint = self._claim_fingerprint(move.claim)
                        recorder.emit(
                            "move_proposed",
                            {
                                "move": move.model_dump(),
                                "raw_model_json": move.model_dump(),
                                "claim_fingerprint": fingerprint,
                            },
                            depth=depth,
                            state_id=state.id,
                        )

                        evaluation, experiments = self._evaluate_move(problem, state, move)
                        disagreement = self._checker_disagreement(evaluation, experiments)
                        novelty = self._novelty_score(move.claim, state.accepted_claims)
                        novelty_history.append(novelty)

                        milestones_hit = self._milestones_hit(problem, move)
                        achieved = set(state.assumptions)
                        newly_achieved = [f"milestone:{m}" for m in milestones_hit if f"milestone:{m}" not in achieved]
                        milestone_bonus = 2.0 if newly_achieved else 0.0

                        move_score = score_move_evaluation(evaluation, move)
                        if problem.id == "erdos_004" and not newly_achieved:
                            move_score -= 2.0

                        new_state = state.model_copy(deep=True)
                        new_state.id = f"state_{uuid4().hex[:8]}"
                        new_state.depth = depth
                        new_state.moves.append(move)
                        new_state.evaluations.append(evaluation)
                        new_state.experiments.extend(experiments)
                        new_state.retrieved_lemmas = [r.item_id for r in retrieved]
                        new_state.assumptions.extend(newly_achieved)

                        if evaluation.status in {"verified_formally", "accepted_computationally", "already_known"} and novelty > 0.01:
                            new_state.accepted_claims.append(move.claim)
                        elif evaluation.status == "rejected_by_counterexample":
                            new_state.rejected_claims.append(move.claim)
                        elif evaluation.status == "plausible_informal":
                            new_state.subgoals.append(f"formalize: {move.claim}")

                        new_state.score = score_state(
                            previous_score=state.score,
                            move_scores=[move_score + milestone_bonus],
                            depth=depth,
                            novelty=novelty,
                        )
                        new_state.trace.append(
                            f"depth={depth} move={move.id} status={evaluation.status} novelty={novelty:.2f} milestones={milestones_hit} score={new_state.score:.2f}"
                        )

                        rejection_category = evaluation.evidence.get("rejection_category", "none")
                        recorder.emit(
                            "move_evaluated",
                            {
                                "move": move.model_dump(),
                                "evaluation": evaluation.model_dump(),
                                "score": new_state.score,
                                "state": new_state.model_dump(),
                                "claim_fingerprint": fingerprint,
                                "rejection_reason_category": rejection_category,
                                "checker_disagreement_summary": disagreement,
                                "novelty": novelty,
                                "milestones_hit": milestones_hit,
                            },
                            depth=depth,
                            state_id=new_state.id,
                        )
                        candidates.append(new_state)

                if not candidates:
                    final_status = "failed"
                    recorder.emit("status_changed", {"status": final_status}, depth=depth)
                    break

                candidates.sort(key=lambda s: s.score, reverse=True)
                beam = candidates[: self.config.beam_width]
                best_scores.append(beam[0].score)
                LOG.info("depth=%s best_score=%.2f", depth, beam[0].score)

                if any(self._is_target_solved(problem, s) for s in beam):
                    final_status = "verified_solution"
                    recorder.emit("status_changed", {"status": final_status}, depth=depth)
                    break

                stalled_numeric = is_stalled(best_scores, self.config.stall_threshold)
                stalled_semantic = is_semantically_stalled(novelty_history, self.config.stall_threshold)
                if stalled_numeric or stalled_semantic:
                    recorder.emit(
                        "stall_detected",
                        {
                            "best_scores": best_scores[-(self.config.stall_threshold + 1):],
                            "novelty_tail": novelty_history[-self.config.stall_threshold :],
                            "reason": "semantic" if stalled_semantic else "numeric",
                        },
                        depth=depth,
                    )
                    if self.config.use_rlm:
                        for existing in beam:
                            existing.trace.append("rlm triggered after stall")
                        failures = self.failure_store.search_failures(problem.id, problem.statement, top_k=10)
                        solved_cases = self.case_retriever.retrieve(problem, top_k=3) if self.case_retriever else []
                        rlm_out = self.rlm.run(problem, beam, failures, solved_cases)
                        rlm_notes = rlm_out.model_dump()
                        recorder.emit(
                            "rlm_started",
                            {"failure_analysis": rlm_out.failure_analysis, "subproblems": rlm_out.subproblems},
                            depth=depth,
                        )
                        ranked = sorted(
                            rlm_out.candidate_moves,
                            key=lambda mv: self._rlm_relevance_score(mv, beam[0], problem),
                            reverse=True,
                        )
                        for rank, move in enumerate(ranked, start=1):
                            recorder.emit(
                                "candidate_move_ranked",
                                {"rank": rank, "move": move.model_dump()},
                                depth=depth,
                            )
                            state = beam[0]
                            evaluation, experiments = self._evaluate_move(problem, state, move)
                            new_state = state.model_copy(deep=True)
                            new_state.id = f"state_{uuid4().hex[:8]}"
                            new_state.depth = depth
                            new_state.moves.append(move)
                            new_state.evaluations.append(evaluation)
                            new_state.experiments.extend(experiments)
                            novelty = self._novelty_score(move.claim, state.accepted_claims)
                            novelty_history.append(novelty)
                            new_state.score = score_state(
                                state.score,
                                [score_move_evaluation(evaluation, move)],
                                depth,
                                novelty=novelty,
                            )
                            new_state.trace.append(f"rlm injection move={move.id} status={evaluation.status}")
                            beam.append(new_state)
                            recorder.emit(
                                "rlm_injected",
                                {
                                    "move": move.model_dump(),
                                    "evaluation": evaluation.model_dump(),
                                    "score": new_state.score,
                                    "state": new_state.model_dump(),
                                    "novelty": novelty,
                                },
                                depth=depth,
                                state_id=new_state.id,
                            )
                        beam.sort(key=lambda s: s.score, reverse=True)
                        beam = beam[: self.config.beam_width]
                    else:
                        final_status = "stalled"
                        recorder.emit("status_changed", {"status": final_status}, depth=depth)
                        break
        except Exception as exc:  # noqa: BLE001
            recorder.emit("error", {"message": str(exc)})
            raise
        finally:
            if previous_debug_dir is None:
                os.environ.pop("ERDOS_LLM_DEBUG_DIR", None)
            else:
                os.environ["ERDOS_LLM_DEBUG_DIR"] = previous_debug_dir

        best_state = max(beam, key=lambda s: s.score)
        if final_status == "failed":
            if any(ev.status == "rejected_by_counterexample" for ev in best_state.evaluations):
                final_status = "counterexample_found"
            elif best_state.evaluations:
                final_status = "plausible_progress"
            else:
                final_status = "stalled"
            recorder.emit("status_changed", {"status": final_status})

        recorder.emit("run_finished", {"status": final_status, "rlm_notes": rlm_notes})

        reduced = reduce_run_events(load_events(events_path))
        reduced_best_state = reduced.get("best_state") or best_state
        reduced_status = str(reduced.get("status") or final_status)
        reduced_rlm = reduced.get("rlm_notes") or rlm_notes

        Path(run_session.artifacts.best_state_path).write_text(
            json.dumps(reduced_best_state.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if run_session.artifacts.rlm_notes_path:
            Path(run_session.artifacts.rlm_notes_path).write_text(
                json.dumps(reduced_rlm, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        md_path, _json_path = write_run_report_from_session(
            session=run_session,
            problem=problem,
            best_state=reduced_best_state,
            final_status=reduced_status,
            rlm_notes=reduced_rlm,
        )

        write_run_report(
            reports_dir=self.reports_dir,
            problem=problem,
            config=run_config,
            best_state=reduced_best_state,
            final_status=reduced_status,
            rlm_notes=reduced_rlm,
            lean_preflight=lean_preflight,
        )

        manifest = {
            "run_id": run_session.run_id,
            "problem_id": run_session.problem_id,
            "status": reduced_status,
            "config": run_session.config,
            "lean_preflight": lean_preflight,
            "artifacts": run_session.artifacts.model_dump(),
        }
        Path(run_session.artifacts.manifest_path).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        summary = f"status={reduced_status} score={reduced_best_state.score:.2f} depth={reduced_best_state.depth}"
        return RunResult(
            problem_id=problem.id,
            status=reduced_status,  # type: ignore[arg-type]
            best_state=reduced_best_state,
            report_path=md_path,
            summary=summary,
            run_id=run_session.run_id,
            attempt_dir=run_session.artifacts.attempt_dir,
            artifacts=run_session.artifacts,
        )
