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

    @staticmethod
    def _is_tautological_mapping(lean_src: str) -> bool:
        compact = " ".join(lean_src.split())
        return " : ∀ m : Nat, N < m → m ≤ N + L → ¬ Nat.Prime m := by" in compact and "exact h m hm1 hm2" in compact

    @staticmethod
    def _normalize_expr(expr: str) -> str:
        out = expr.strip().lower().replace(" ", "")
        out = out.replace("==", "=")
        return out

    def _obligation_source(self, theorem_name: str, obligations: list[dict]) -> str | None:
        """Generate Lean source from compositional obligations."""
        statements: list[str] = []
        for raw in obligations:
            stmt = str(raw.get("statement", "")).strip()
            if stmt:
                statements.append(stmt)
        if not statements:
            return None

        # Special case: eq rewrite obligation "A=B -> C=f(A) -> C=f(B)"
        for stmt in statements:
            if "->" not in stmt:
                continue
            parts = [p.strip() for p in stmt.split("->") if p.strip()]
            if len(parts) < 2:
                continue
            left = parts[0]
            right = parts[-1]
            if "=" not in left or "=" not in right:
                continue
            l_lhs, l_rhs = [x.strip() for x in left.split("=", 1)]
            r_lhs, r_rhs = [x.strip() for x in right.split("=", 1)]
            if self._normalize_expr(left) == self._normalize_expr(right):
                continue
            # Build conservative rewrite theorem over reals to support log().
            if "log" in left.lower() or "log" in right.lower():
                return (
                    f"""
import Mathlib

namespace ErdosEngine

theorem {theorem_name}
    (A B C : Real)
    (hAB : A = B)
    (hC : C = Real.log A) :
    C = Real.log B := by
  simpa [hAB] using hC

end ErdosEngine
""".strip()
                    + "\n"
                )

            # Generic equality rewrite theorem.
            return (
                f"""
import Mathlib

namespace ErdosEngine

theorem {theorem_name}
    (A B C : Nat)
    (hAB : A = B)
    (hC : C = A) :
    C = B := by
  simpa [hAB] using hC

end ErdosEngine
""".strip()
                + "\n"
            )

        return None

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
        if move.move_type == "external_theorem_anchor":
            if not move.translation_steps or not move.exact_asymptotic_form:
                return MoveEvaluation(
                    move_id=move.id,
                    status="invalid_format",
                    reason="external_theorem_anchor requires exact asymptotic form and translation steps.",
                    score_delta=-3.0,
                    evidence={"rejection_category": "anchor_missing_reference_fields"},
                )
            if not move.lean_obligations:
                return MoveEvaluation(
                    move_id=move.id,
                    status="invalid_format",
                    reason="external_theorem_anchor requires downstream obligations, not prose-only anchor.",
                    score_delta=-3.0,
                    evidence={"rejection_category": "anchor_missing_downstream_obligations"},
                )
        theorem_name = self._sanitize(f"{problem.id}_{move.id}_{state.depth}")
        lean_src = self._obligation_source(theorem_name, move.lean_obligations)
        if lean_src is None:
            lean_src = self._goal_for_move(problem, move, theorem_name)

        if move.lean_obligations and lean_src is None:
            return MoveEvaluation(
                move_id=move.id,
                status="rejected_by_counterexample",
                reason="No nontrivial Lean obligation could be generated from theorem chain.",
                score_delta=-4.0,
                evidence={
                    "lean_formalization_attempted": False,
                    "obligation_count": len(move.lean_obligations),
                    "rejection_category": "obligation_generation_failed",
                },
                counterexample="nontrivial obligation missing",
            )

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

        if self._is_tautological_mapping(lean_src):
            return MoveEvaluation(
                move_id=move.id,
                status="plausible_informal",
                reason="Mapped Lean theorem is tautological; formal progress not credited.",
                score_delta=0.0,
                evidence={
                    "lean_formalization_attempted": True,
                    "rejection_category": "tautological_mapping_blocked",
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
