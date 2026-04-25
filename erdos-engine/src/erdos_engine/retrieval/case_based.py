"""Solved-case retrieval for path guidance."""

from __future__ import annotations

from collections import Counter

from erdos_engine.store.problem_store import ProblemStore


class SolvedCaseRetriever:
    """Retrieve solved cases and summarize steps + why they worked."""

    def __init__(self, problem_store: ProblemStore) -> None:
        self.problem_store = problem_store

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t.strip(".,:;()[]{}!?\n\t").lower() for t in text.split() if t.strip()}

    @staticmethod
    def _extract_steps_and_why(text: str) -> tuple[list[str], list[str]]:
        chunks = [c.strip() for c in text.replace("\n", " ").split(".") if c.strip()]
        steps = chunks[:5]
        why = [
            c
            for c in chunks
            if any(k in c.lower() for k in ["because", "therefore", "thus", "so that", "proved by", "using"])
        ][:5]
        return steps, why

    def retrieve(self, query_problem, top_k: int = 3) -> list[dict]:
        q_tokens = self._tokens(f"{query_problem.title} {query_problem.statement}")
        out: list[tuple[float, dict]] = []
        for p in self.problem_store.list_problems():
            if p.id == query_problem.id:
                continue
            if p.status != "solved":
                continue

            known_solution = self.problem_store.get_known_solution(p.id) or ""
            body = f"{p.title} {p.statement} {known_solution}"
            p_tokens = self._tokens(body)

            overlap = len(q_tokens.intersection(p_tokens))
            tag_overlap = len(set(query_problem.tags).intersection(set(p.tags)))
            score = float(overlap + 3 * tag_overlap)
            if score <= 0:
                continue

            steps, why = self._extract_steps_and_why(known_solution or p.statement)
            out.append(
                (
                    score,
                    {
                        "case_id": p.id,
                        "title": p.title,
                        "statement": p.statement,
                        "tags": p.tags,
                        "steps_taken": steps,
                        "why_they_worked": why,
                        "source_url": p.source_url,
                    },
                )
            )

        out.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in out[:top_k]]
