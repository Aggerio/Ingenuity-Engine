from pathlib import Path

from erdos_engine.models import Lemma
from erdos_engine.store.lemma_store import LemmaStore


def test_load_lemma_db() -> None:
    store = LemmaStore(Path("data"))
    lemmas = store.load_lemmas()
    assert len(lemmas) >= 1


def test_add_lemma(tmp_path: Path) -> None:
    root = tmp_path / "data"
    (root / "lemma_db").mkdir(parents=True)
    (root / "lemma_db" / "lemmas.jsonl").write_text("", encoding="utf-8")
    (root / "lemma_db" / "proof_moves.jsonl").write_text("", encoding="utf-8")

    store = LemmaStore(root)
    lemma = Lemma(
        id="l1",
        title="t",
        statement="s",
        domain_tags=["x"],
        conditions=[],
        conclusion="c",
        proof_strategy=None,
        dependencies=[],
        used_in=[],
        source=None,
        formal_status="informal",
        failure_modes=[],
    )
    store.add_lemma(lemma)
    loaded = store.load_lemmas()
    assert loaded[0].id == "l1"
