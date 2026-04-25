import json
from pathlib import Path

from erdos_engine.ingestion import bootstrap_from_previous_info, import_erdos_problem
from erdos_engine.store.lemma_store import LemmaStore


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_import_erdos_problem_parses_html(monkeypatch, tmp_path: Path) -> None:
    html = '''
    <div class="problem-text" id="solved">
      <span class="tooltip">PROVED<span class="tooltiptext">This has been solved.</span></span>
      <div id="content">Is it true that all examples satisfy X?</div>
      <div id="tags"><a href="/tags/number theory">number theory</a></div>
    </div>
    <div class="problem-additional-text">Solved by Someone [Ref].</div>
    <p style="text-align: center; font-family: 'Courier New', monospace; font-size: 90%;">x</p>
    '''

    def _fake_get(url: str, timeout: int):
        return _Resp(html)

    monkeypatch.setattr("erdos_engine.ingestion.erdos_problem.requests.get", _fake_get)
    problem_id = import_erdos_problem(4, tmp_path)
    assert problem_id == "erdos_004"

    meta = json.loads((tmp_path / "problems" / problem_id / "metadata.json").read_text())
    assert meta["status"] == "solved"
    assert "number theory" in meta["tags"]
    assert (tmp_path / "problems" / problem_id / "statement.md").exists()


def test_bootstrap_from_previous_info_dedup(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    previous_root = tmp_path / "previous-info"
    np_dir = previous_root / "naturalproofs"
    np_dir.mkdir(parents=True)

    payload = {
        "dataset": {
            "theorems": [
                {"id": 1, "title": "T1", "contents": ["A implies B"], "recursive_categories": ["Number Theory"]},
                {"id": 2, "title": "T1", "contents": ["A implies B"], "recursive_categories": ["Number Theory"]},
            ],
            "definitions": [],
        }
    }
    (np_dir / "naturalproofs_test.json").write_text(json.dumps(payload), encoding="utf-8")

    store = LemmaStore(data_dir)
    out = bootstrap_from_previous_info(previous_root, store)
    assert out["lemmas_added"] == 1
    assert out["moves_added"] == 1
