"""Failure memory store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class FailureStore:
    """Append-only failure memory for rejected moves."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "lemma_db" / "failures.jsonl"

    def record_failure(
        self,
        problem_id: str,
        move: dict[str, Any],
        reason_failed: str,
        counterexample: str | None,
        checker_output: dict[str, Any],
        reusable_warning: str,
    ) -> None:
        row = {
            "problem_id": problem_id,
            "move": move,
            "reason_failed": reason_failed,
            "counterexample": counterexample,
            "checker_output": checker_output,
            "reusable_warning": reusable_warning,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    def search_failures(self, problem_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        terms = {t for t in query.lower().split() if t}
        scored: list[tuple[float, dict[str, Any]]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("problem_id") != problem_id:
                continue
            text = json.dumps(row, ensure_ascii=False).lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                scored.append((float(score), row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scored[:top_k]]
