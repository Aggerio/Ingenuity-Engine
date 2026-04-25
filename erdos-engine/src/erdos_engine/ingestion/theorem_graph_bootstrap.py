"""Build theorem graph candidates from lemma DB content."""

from __future__ import annotations

import hashlib
import re

from erdos_engine.models import DerivationEdge, TheoremNode
from erdos_engine.store.lemma_store import LemmaStore
from erdos_engine.store.theorem_graph_store import TheoremGraphStore


_SYM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def normalize_statement(text: str) -> str:
    """Normalize textual statement for weak equivalence matching."""
    base = re.sub(r"\s+", " ", text.strip().lower())
    base = base.replace("==", "=")
    base = re.sub(r"\s*=\s*", " = ", base)
    return re.sub(r"[^a-z0-9_=+\-*/()<> ]", "", base)


def extract_symbols(text: str) -> list[str]:
    """Extract coarse symbol list from statement."""
    seen: set[str] = set()
    out: list[str] = []
    for token in _SYM_RE.findall(text):
        t = token.lower()
        if t in {"let", "for", "all", "exists", "then", "and", "or"}:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:20]


def infer_rule_type(statement: str) -> str:
    low = statement.lower()
    if "mod" in low or "congruence" in low or "congruent" in low:
        return "congruence_composition"
    if "=" in statement:
        return "rewrite"
    if any(k in low for k in ["implies", "then", "therefore", "iff"]):
        return "composition"
    return "specialization"


def _node_id(source_id: str, normalized: str) -> str:
    digest = hashlib.sha1(f"{source_id}::{normalized}".encode("utf-8")).hexdigest()[:16]
    return f"node_{digest}"


def _edge_id(node_id: str, rule_type: str) -> str:
    digest = hashlib.sha1(f"{node_id}::{rule_type}".encode("utf-8")).hexdigest()[:16]
    return f"edge_{digest}"


def bootstrap_theorem_graph(lemma_store: LemmaStore, graph_store: TheoremGraphStore) -> dict:
    """Auto-extract theorem graph candidates from existing memory."""
    nodes: dict[str, TheoremNode] = {node.node_id: node for node in graph_store.load_nodes()}
    edges: dict[str, DerivationEdge] = {edge.edge_id: edge for edge in graph_store.load_edges()}

    added_nodes = 0
    added_edges = 0

    for lemma in lemma_store.load_lemmas():
        normalized = normalize_statement(lemma.statement or lemma.conclusion or lemma.title)
        if not normalized:
            continue
        node_id = _node_id(lemma.id, normalized)
        if node_id not in nodes:
            nodes[node_id] = TheoremNode(
                node_id=node_id,
                source_id=lemma.id,
                statement=lemma.statement or lemma.title,
                normalized_statement=normalized,
                domain="number_theory" if "prime" in normalized else "generic",
                kind="candidate",
                symbols=extract_symbols(lemma.statement),
                assumptions=list(lemma.conditions),
                conclusion=lemma.conclusion or lemma.title,
                metadata={"source_type": "lemma"},
            )
            added_nodes += 1

    for move in lemma_store.load_proof_moves():
        normalized = normalize_statement(move.claim)
        if not normalized:
            continue
        node_id = _node_id(move.id, normalized)
        if node_id not in nodes:
            nodes[node_id] = TheoremNode(
                node_id=node_id,
                source_id=move.id,
                statement=move.claim,
                normalized_statement=normalized,
                domain="number_theory" if "prime" in normalized or "mod" in normalized else "generic",
                kind="candidate",
                symbols=extract_symbols(move.claim),
                assumptions=list(move.required_preconditions),
                conclusion=move.claim,
                metadata={"source_type": "proof_move", "move_type": move.move_type},
            )
            added_nodes += 1

        rule_type = infer_rule_type(move.claim)
        edge_id = _edge_id(node_id, rule_type)
        if edge_id not in edges:
            edges[edge_id] = DerivationEdge(
                edge_id=edge_id,
                from_node_ids=[node_id],
                to_node_id=node_id,
                rule_type=rule_type,  # type: ignore[arg-type]
                preconditions=list(move.required_preconditions),
                metadata={"source_move_id": move.id},
            )
            added_edges += 1

    graph_store.save_nodes(list(nodes.values()))
    graph_store.save_edges(list(edges.values()))
    return {
        "nodes_total": len(nodes),
        "edges_total": len(edges),
        "nodes_added": added_nodes,
        "edges_added": added_edges,
    }
