"""Lemma and proof-move JSONL store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from erdos_engine.models import Lemma, ProofMove


class LemmaStore:
    """Persistent store for lemmas and proof move memory."""

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "lemma_db"
        self.lemmas_path = self.root / "lemmas.jsonl"
        self.moves_path = self.root / "proof_moves.jsonl"

    def load_lemmas(self) -> list[Lemma]:
        return [Lemma(**row) for row in self._read_jsonl(self.lemmas_path)]

    def load_proof_moves(self) -> list[ProofMove]:
        return [ProofMove(**row) for row in self._read_jsonl(self.moves_path)]

    def add_lemma(self, lemma: Lemma) -> None:
        self._append_jsonl(self.lemmas_path, lemma.model_dump())

    def add_proof_move(self, move: ProofMove) -> None:
        self._append_jsonl(self.moves_path, move.model_dump())

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
