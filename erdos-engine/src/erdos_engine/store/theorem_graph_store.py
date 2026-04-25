"""JSONL-backed theorem graph storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from erdos_engine.models import DerivationEdge, TheoremNode


class TheoremGraphStore:
    """Persistent storage for theorem nodes and derivation edges."""

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "theorem_graph"
        self.nodes_path = self.root / "nodes.jsonl"
        self.edges_path = self.root / "edges.jsonl"

    def load_nodes(self) -> list[TheoremNode]:
        return [TheoremNode(**row) for row in self._read_jsonl(self.nodes_path)]

    def load_edges(self) -> list[DerivationEdge]:
        return [DerivationEdge(**row) for row in self._read_jsonl(self.edges_path)]

    def save_nodes(self, nodes: list[TheoremNode]) -> None:
        self._write_jsonl(self.nodes_path, [node.model_dump() for node in nodes])

    def save_edges(self, edges: list[DerivationEdge]) -> None:
        self._write_jsonl(self.edges_path, [edge.model_dump() for edge in edges])

    def add_or_replace_node(self, node: TheoremNode) -> None:
        nodes = {existing.node_id: existing for existing in self.load_nodes()}
        nodes[node.node_id] = node
        self.save_nodes(list(nodes.values()))

    def add_or_replace_edge(self, edge: DerivationEdge) -> None:
        edges = {existing.edge_id: existing for existing in self.load_edges()}
        edges[edge.edge_id] = edge
        self.save_edges(list(edges.values()))

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")
