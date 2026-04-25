from pathlib import Path

from erdos_engine.checkers.lean import LeanChecker
from erdos_engine.ingestion.theorem_graph_bootstrap import bootstrap_theorem_graph
from erdos_engine.models import DerivationEdge, Problem, ProofMove, ResearchState, TheoremNode
from erdos_engine.retrieval.theorem_graph import TheoremGraphPlanner
from erdos_engine.store.lemma_store import LemmaStore
from erdos_engine.store.theorem_graph_store import TheoremGraphStore


def _problem() -> Problem:
    return Problem(
        id="pid",
        title="t",
        statement="some statement",
        tags=[],
        status="solved",
        known_solution_path=None,
        source_url=None,
        difficulty_guess=None,
        computationally_testable=True,
        formalizable=True,
    )


def test_theorem_graph_bootstrap_populates_nodes_edges(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    lemma_store = LemmaStore(data_dir)
    graph_store = TheoremGraphStore(data_dir)
    lemma_store.add_proof_move(
        ProofMove(
            id="m",
            move_type="auxiliary_lemma",
            claim="A = B",
            rationale="",
            test_plan="",
            dependencies=[],
            expected_effect="",
            risk=None,
            source="llm",
        )
    )
    result = bootstrap_theorem_graph(lemma_store, graph_store)
    assert result["nodes_total"] >= 1
    assert result["edges_total"] >= 1


def test_planner_composes_symbol_chain() -> None:
    nodes = [
        TheoremNode(
            node_id="n1",
            source_id="s1",
            statement="A = B",
            normalized_statement="a = b",
            symbols=["a", "b"],
            conclusion="A = B",
        ),
        TheoremNode(
            node_id="n2",
            source_id="s2",
            statement="C = log(A)",
            normalized_statement="c = log(a)",
            symbols=["c", "a", "log"],
            conclusion="C = log(A)",
        ),
        TheoremNode(
            node_id="n3",
            source_id="s3",
            statement="C = D",
            normalized_statement="c = d",
            symbols=["c", "d"],
            conclusion="C = D",
        ),
    ]
    edges = [
        DerivationEdge(edge_id="e1", from_node_ids=["n1"], to_node_id="n2", rule_type="rewrite"),
        DerivationEdge(edge_id="e2", from_node_ids=["n2"], to_node_id="n3", rule_type="substitute"),
    ]
    planner = TheoremGraphPlanner(nodes, edges)
    chains = planner.propose_chains("derive D = log(B)", top_k=3, max_hops=2)
    assert chains
    assert any(len(chain.edge_ids) >= 2 for chain in chains)


def test_lean_checker_blocks_tautology_mapping(tmp_path: Path) -> None:
    checker = LeanChecker(project_dir=tmp_path, timeout_seconds=2)
    move = ProofMove(
        id="m1",
        move_type="reduction",
        claim="Assume interval (N, N+L] contains no primes; derive prime gap lower bound",
        rationale="",
        test_plan=None,
        dependencies=[],
        expected_effect="",
        risk=None,
        source="llm",
    )
    ev = checker.evaluate(_problem(), ResearchState(id="s", problem_id="p"), move)
    assert ev.status == "plausible_informal"
    assert ev.evidence["rejection_category"] == "tautological_mapping_blocked"


def test_lean_checker_obligation_rewrite_path(monkeypatch, tmp_path: Path) -> None:
    checker = LeanChecker(project_dir=tmp_path, timeout_seconds=2)
    move = ProofMove(
        id="m2",
        move_type="reduction",
        claim="derive D = log(B)",
        rationale="",
        test_plan=None,
        dependencies=[],
        expected_effect="",
        risk=None,
        source="llm",
        lean_obligations=[{"statement": "A = B -> C = log(A) -> C = log(B)", "source_edge_id": "e1"}],
    )

    class Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Proc())
    ev = checker.evaluate(_problem(), ResearchState(id="s", problem_id="p"), move)
    assert ev.status == "verified_formally"
    assert ev.evidence["lean_formalization_attempted"] is True
