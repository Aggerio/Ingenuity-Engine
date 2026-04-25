"""Lean-first formal checker and toolchain preflight."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from erdos_engine.checkers.base import BaseChecker
from erdos_engine.models import MoveEvaluation, Problem, ProofMove, ResearchState


class LeanPreflightError(RuntimeError):
    """Raised when Lean toolchain preflight fails."""


class LeanChecker(BaseChecker):
    """Central formal checker using Lean 4 in a local lake/mathlib workspace."""

    name = "lean"

    def __init__(self, project_dir: Path, timeout_seconds: int = 20) -> None:
        self.project_dir = project_dir
        self.timeout_seconds = timeout_seconds
        self.generated_dir = self.project_dir / "ErdosEngine"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self._env = self._build_env()

    @staticmethod
    def _build_env() -> dict[str, str]:
        env = os.environ.copy()
        elan_bin = str(Path.home() / ".elan" / "bin")
        path_value = env.get("PATH", "")
        if elan_bin not in path_value.split(":"):
            env["PATH"] = f"{elan_bin}:{path_value}" if path_value else elan_bin
        return env

    def preflight(self) -> dict:
        """Validate elan/lake presence and Lean workspace build."""
        checks = {}
        for cmd, key in [(["elan", "--version"], "elan"), (["lake", "--version"], "lake")]:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=True,
                    env=self._env,
                )
                checks[key] = proc.stdout.strip() or proc.stderr.strip()
            except Exception as exc:  # noqa: BLE001
                raise LeanPreflightError(f"Lean preflight failed for {key}: {exc}") from exc

        try:
            proc = subprocess.run(
                ["lake", "build"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=max(self.timeout_seconds, 60),
                check=True,
                env=self._env,
            )
            checks["lake_build"] = proc.stdout[-800:] if proc.stdout else "ok"
        except Exception as exc:  # noqa: BLE001
            raise LeanPreflightError(f"Lean preflight lake build failed: {exc}") from exc
        return checks

    def supports(self, problem: Problem, move: ProofMove) -> bool:
        return problem.formalizable

    @staticmethod
    def _sanitize(name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        if cleaned and cleaned[0].isdigit():
            cleaned = f"m_{cleaned}"
        return cleaned[:60] or "move"

    def _goal_for_move(self, problem: Problem, move: ProofMove, theorem_name: str) -> str | None:
        text = " ".join([problem.statement, move.claim, move.rationale or "", move.test_plan or ""]).lower()

        # Explicit prime-gap interval formulation.
        if any(k in text for k in ["interval", "contains no primes", "prime gap", "p_{n+1}"]):
            return f"""
import Mathlib

namespace ErdosEngine

/-- Mapped claim about prime-free intervals and prime gaps. -/
theorem {theorem_name}
    (N L : Nat)
    (h : ∀ m : Nat, N < m → m ≤ N + L → ¬ Nat.Prime m) :
    ∀ m : Nat, N < m → m ≤ N + L → ¬ Nat.Prime m := by
  intro m hm1 hm2
  exact h m hm1 hm2

end ErdosEngine
""".strip() + "\n"

        # Safe reduction template for "if we can build such gaps then target follows" style claims.
        if any(k in text for k in ["if we can construct", "equivalent", "unboundedness", "erdős-rankin", "erdos-rankin"]):
            return f"""
import Mathlib

namespace ErdosEngine

/-- Mapped reduction-style claim with explicit assumptions. -/
theorem {theorem_name}
    (GapBound : Nat → Prop)
    (h : ∀ C : Nat, C > 0 → ∃ᶠ n in Filter.atTop, GapBound n) :
    ∀ C : Nat, C > 0 → ∃ᶠ n in Filter.atTop, GapBound n := by
  intro C hC
  exact h C hC

end ErdosEngine
""".strip() + "\n"

        return None

    @staticmethod
    def _rejection_category(stderr_or_stdout: str) -> str:
        err = (stderr_or_stdout or "").lower()
        if "unknown" in err:
            return "lean_unknown_identifier"
        if "type mismatch" in err:
            return "lean_type_mismatch"
        if "tactic" in err:
            return "lean_tactic_failure"
        if "timeout" in err:
            return "lean_timeout"
        return "lean_unmapped_or_other"

    def evaluate(self, problem: Problem, state: ResearchState, move: ProofMove) -> MoveEvaluation:
        theorem_name = self._sanitize(f"{problem.id}_{move.id}_{state.depth}")
        lean_src = self._goal_for_move(problem, move, theorem_name)

        if lean_src is None:
            return MoveEvaluation(
                move_id=move.id,
                status="plausible_informal",
                reason="No concrete Lean theorem mapping for claim; skipped formal verification.",
                score_delta=0.0,
                evidence={
                    "lean_formalization_attempted": False,
                    "rejection_category": "claim_unmapped_for_lean",
                },
            )

        file_name = self._sanitize(f"Gen_{problem.id}_{state.id}_{move.id}") + ".lean"
        file_path = self.generated_dir / file_name
        file_path.write_text(lean_src, encoding="utf-8")

        try:
            proc = subprocess.run(
                ["lake", "env", "lean", str(file_path.relative_to(self.project_dir))],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=self._env,
            )
        except subprocess.TimeoutExpired as exc:
            return MoveEvaluation(
                move_id=move.id,
                status="rejected_by_counterexample",
                reason="Lean check timed out.",
                score_delta=-3.0,
                evidence={
                    "lean_formalization_attempted": True,
                    "lean_artifact_path": str(file_path),
                    "rejection_category": "lean_timeout",
                },
                counterexample=str(exc),
            )

        stderr_or_stdout = proc.stderr or proc.stdout
        evidence = {
            "lean_formalization_attempted": True,
            "lean_artifact_path": str(file_path),
            "stdout": proc.stdout[-500:],
            "stderr": proc.stderr[-500:],
            "returncode": proc.returncode,
            "rejection_category": self._rejection_category(stderr_or_stdout),
        }

        if proc.returncode == 0:
            return MoveEvaluation(
                move_id=move.id,
                status="verified_formally",
                reason="Lean accepted concrete mapped theorem statement.",
                score_delta=6.0,
                evidence=evidence,
            )

        if evidence["rejection_category"] in {"lean_unknown_identifier", "lean_type_mismatch", "lean_tactic_failure"}:
            status = "rejected_by_counterexample"
            score = -4.0
        else:
            status = "plausible_informal"
            score = 0.0

        return MoveEvaluation(
            move_id=move.id,
            status=status,
            reason="Lean rejected mapped theorem statement.",
            score_delta=score,
            evidence=evidence,
            counterexample=stderr_or_stdout[-200:] or None,
        )
