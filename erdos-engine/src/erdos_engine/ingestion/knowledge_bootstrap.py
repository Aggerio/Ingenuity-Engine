"""Bootstrap lemma/proof-move memory from previous-info corpora."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from erdos_engine.models import Lemma, ProofMove
from erdos_engine.store.lemma_store import LemmaStore


def _fingerprint(*parts: str) -> str:
    payload = "||".join(p.strip().lower() for p in parts if p)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _safe_text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(str(x).strip() for x in value if str(x).strip())
    return str(value).strip()


def _load_naturalproofs_entries(path: Path) -> list[tuple[str, dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    dataset = data.get("dataset", {})
    out: list[tuple[str, dict]] = []
    for group in ("theorems", "definitions"):
        for item in dataset.get(group, []):
            if isinstance(item, dict):
                out.append((group, item))
    return out


def bootstrap_from_previous_info(previous_info_root: Path, lemma_store: LemmaStore) -> dict:
    """Ingest naturalproofs JSON into lemmas and proof moves with dedupe."""
    natural_dir = previous_info_root / "naturalproofs"
    files = sorted(natural_dir.glob("naturalproofs_*.json"))

    existing_lemmas = lemma_store.load_lemmas()
    existing_moves = lemma_store.load_proof_moves()
    seen_lemma = {_fingerprint(l.title, l.statement, l.conclusion) for l in existing_lemmas}
    seen_move = {_fingerprint(m.move_type, m.claim) for m in existing_moves}

    added_lemmas = 0
    added_moves = 0
    for file_path in files:
        source_name = file_path.stem
        entries = _load_naturalproofs_entries(file_path)
        for group, item in entries:
            title = _safe_text(item.get("title") or item.get("label") or "untitled")
            contents = _safe_text(item.get("contents") or "")
            categories = item.get("recursive_categories") or item.get("categories") or []
            tags = [str(t).strip().lower().replace(" ", "_") for t in categories if str(t).strip()]
            statement = contents[:1200] if contents else title
            conclusion = title

            lemma_key = _fingerprint(title, statement, conclusion)
            if lemma_key not in seen_lemma:
                lemma = Lemma(
                    id=f"lemma_{source_name}_{lemma_key}",
                    title=title,
                    statement=statement,
                    domain_tags=tags[:8],
                    conclusion=conclusion,
                    proof_strategy="Imported from naturalproofs corpus",
                    source=source_name,
                    formal_status="informal",
                )
                lemma_store.add_lemma(lemma)
                seen_lemma.add(lemma_key)
                added_lemmas += 1

            move_type = "auxiliary_lemma" if group == "theorems" else "reformulation"
            claim = title
            move_key = _fingerprint(move_type, claim)
            if move_key in seen_move:
                continue
            test_plan = "check bounded instances / known special cases"
            move = ProofMove(
                id=f"move_{source_name}_{move_key}",
                move_type=move_type,  # type: ignore[arg-type]
                claim=claim,
                rationale=(contents[:500] if contents else f"Imported from {source_name}"),
                test_plan=test_plan,
                dependencies=[],
                expected_effect="introduce reusable lemma-level direction",
                risk="low",
                source="lemma_db",
            )
            lemma_store.add_proof_move(move)
            seen_move.add(move_key)
            added_moves += 1

    return {
        "files_scanned": len(files),
        "lemmas_added": added_lemmas,
        "moves_added": added_moves,
    }
