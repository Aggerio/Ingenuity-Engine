from pathlib import Path

from erdos_engine.store.problem_store import ProblemStore


def test_load_sample_problems() -> None:
    store = ProblemStore(Path("data"))
    probs = store.list_problems()
    ids = {p.id for p in probs}
    assert "sample_solved_001" in ids
    assert "sample_solved_002" in ids


def test_show_problem_fields() -> None:
    store = ProblemStore(Path("data"))
    p = store.get_problem("sample_solved_001")
    assert "prime" in p.statement.lower()
    assert p.status == "solved"
