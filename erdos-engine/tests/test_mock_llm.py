from erdos_engine.llm.mock import MockLLMClient


def test_mock_llm_returns_moves() -> None:
    llm = MockLLMClient(seed=1)
    moves = llm.generate_moves("prime", 3)
    assert len(moves) == 3
    assert all(m.move_type in {"construction", "brute_force_experiment"} for m in moves)
