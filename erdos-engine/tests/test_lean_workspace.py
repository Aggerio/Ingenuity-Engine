from pathlib import Path


def test_lean_workspace_root_module_exists() -> None:
    root = Path("lean_workspace") / "ErdosEngine.lean"
    assert root.exists()
    text = root.read_text(encoding="utf-8")
    assert "import ErdosEngine.Main" in text
