# erdos-engine

Lean-first local proof-search and research harness for Erdős-style problems.

## What It Is
`erdos-engine` is a local system where the LLM is a move proposer, not a proof oracle.
The harness retrieves prior lemmas/failures, proposes candidate moves, tests and ranks them,
verifies formalizable steps with Lean, and emits inspectable reports.

## Core Philosophy
- LLM output is never trusted by default.
- Every move is parsed as JSON and evaluated.
- Lean verification is central; computational checkers are secondary support.
- Failure memory is persistent to reduce loops.
- Useful partial progress and transparent traces are success in v0.

## How Beam Search Works
1. Start from the problem statement as initial subgoal.
2. Retrieve relevant lemmas/proof moves/failures.
3. Ask LLM for structured candidate moves.
4. Evaluate each move with Lean first, then heuristic checkers.
5. Score new research states and keep top-k beam states.
6. If stalled, trigger recursive RLM mode and inject synthesized moves.
7. End with verified solution or best partial result.

## What RLM Mode Does
When search stalls, RLM mode:
- summarizes failures,
- proposes reformulations/subproblems,
- runs specialized agent perspectives,
- synthesizes candidate moves,
- re-injects best moves into beam search.

## Install
```bash
pip install -e ".[dev]"
```

Optional z3 support:
```bash
pip install -e ".[z3]"
```

## Environment
Copy `.env.example` and set values as needed.

OpenRouter via OpenAI-compatible API is supported with:
- `OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api`
- `OPENAI_COMPATIBLE_API_KEY=...`
- `OPENAI_COMPATIBLE_MODEL=openai/gpt-oss-20b:free` (always-free proposer)
- `OPENAI_COMPATIBLE_CRITIC_MODEL=google/gemini-2.5-flash-lite` (Gemini critic/confirmation)

Model selection notes:
- Use the `:free` suffix for explicit free variants.
- `openrouter/free` is also supported, but it randomly picks from free models.

Lean-first defaults:
- `LEAN_PROJECT_DIR=lean_workspace`
- `LEAN_TIMEOUT_SECONDS=20`
- `LEAN_REQUIRED=true`

## Commands
```bash
python -m erdos_engine.cli init-sample-data
python -m erdos_engine.cli list-problems
python -m erdos_engine.cli run sample_solved_001
python -m erdos_engine.cli run sample_solved_002 --use-rlm
```

Additional commands:
```bash
python -m erdos_engine.cli show-problem sample_solved_001
python -m erdos_engine.cli add-lemma --file path/to/lemma.json
python -m erdos_engine.cli report sample_solved_001
```

`report` expects a problem id and returns the latest report file for that problem.

## Sample Problems
Two toy solved calibration problems are included:
1. Infinitely many primes.
2. `R(3,3) <= 6`.

## Data Layout
- `data/problems/...`: problem metadata/statements/known solutions.
- `data/lemma_db/lemmas.jsonl`: known lemmas.
- `data/lemma_db/proof_moves.jsonl`: reusable move patterns.
- `data/lemma_db/failures.jsonl`: persistent failure memory.

## Reports
Each run writes:
- Markdown: `reports/{timestamp}_{problem_id}.md`
- JSON trace: `reports/{timestamp}_{problem_id}.json`

Reports include status, best state, accepted/rejected moves, Lean evidence, RLM findings, and trace.

## Limitations (v0)
- Lean formalization is scaffold-driven and conservative.
- No vector DB or external ingestion yet.
- No web UI.
- Open-problem discovery remains exploratory.

## Roadmap Hooks (TODO)
- Erdős Problems/arXiv ingestion.
- Embedding/vector retrieval backends.
- deeper Lean/mathlib workflows.
- SageMath and SAT-based finite combinatorics.
- theorem statement formalization assistants.
- human review UI/dashboard.
- solved/open benchmark suites.
