"""Problem store for file-backed problem metadata and statements."""

from __future__ import annotations

import json
from pathlib import Path

from erdos_engine.models import Problem


class ProblemStore:
    """Loads problems from data/problems/* directories."""

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "problems"

    def list_problems(self) -> list[Problem]:
        """Return all discovered problems sorted by id."""
        problems: list[Problem] = []
        if not self.root.exists():
            return problems
        for pdir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            problems.append(self._load_problem_dir(pdir))
        return sorted(problems, key=lambda p: p.id)

    def get_problem(self, problem_id: str) -> Problem:
        """Load a single problem by id."""
        pdir = self.root / problem_id
        if not pdir.exists():
            raise FileNotFoundError(f"Problem not found: {problem_id}")
        return self._load_problem_dir(pdir)

    def get_known_solution(self, problem_id: str) -> str | None:
        """Read known solution markdown when available."""
        pdir = self.root / problem_id
        path = pdir / "known_solution.md"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def _load_problem_dir(self, pdir: Path) -> Problem:
        meta_path = pdir / "metadata.json"
        statement_path = pdir / "statement.md"
        if not meta_path.exists() or not statement_path.exists():
            raise FileNotFoundError(f"Missing metadata or statement in {pdir}")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        metadata["statement"] = statement_path.read_text(encoding="utf-8").strip()
        return Problem(**metadata)

    def init_sample_data(self, force: bool = False) -> None:
        """Ensure sample data exists; no-op unless force removes and rewrites files."""
        # Data is committed in repository; this method verifies presence.
        required = [
            self.root / "sample_solved_001" / "metadata.json",
            self.root / "sample_solved_002" / "metadata.json",
        ]
        missing = [p for p in required if not p.exists()]
        if missing and not force:
            raise FileNotFoundError(
                "Sample data missing. Expected committed fixtures under data/problems/."
            )
