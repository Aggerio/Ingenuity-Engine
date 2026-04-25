# Ingenuity Engine

Ingenuity Engine is an experimental research system for attacking mathematical problems with a combination of language models, retrieval, symbolic checking, search, and formal verification.

The long-term goal is simple:

> Build a machine that can study solved mathematical problems, learn useful proof moves, retrieve relevant lemmas, explore possible solution paths, and eventually help discover new proofs for difficult open problems.

The first target domain is Erdős-style mathematics: problems in number theory, combinatorics, graph theory, extremal structures, and related areas where clever reductions, known lemmas, and creative constructions often matter more than brute-force computation.

## Why This Exists

Modern language models can produce impressive mathematical reasoning, but they are unreliable when used alone. They hallucinate lemmas, skip hard steps, and often produce proofs that sound correct but fail under close inspection.

Ingenuity Engine is built around a different idea:

> Do not trust the model blindly. Use the model as a generator of ideas, and surround it with tools that can search, check, reject, refine, and remember.

Instead of asking an LLM to solve a hard problem in one shot, the system treats proof discovery as an iterative process:

1. Read the problem.
2. Retrieve similar solved problems.
3. Retrieve useful lemmas and proof moves.
4. Generate possible attack strategies.
5. Test small cases or counterexamples.
6. Try symbolic or formal verification where possible.
7. Record failures.
8. Reuse what was learned in future attempts.

The goal is not just to generate answers, but to create a feedback loop that becomes better at mathematical exploration over time.

## Core Idea

Ingenuity Engine is inspired by systems like AlphaGeometry, theorem provers, retrieval-augmented generation, and reinforcement-style search.

The system combines several components:

- **Problem database**: stores mathematical problems, statements, known solutions, metadata, and hidden notes for evaluation.
- **Lemma database**: stores reusable mathematical facts, proof moves, failed attempts, and useful patterns.
- **Retrieval system**: finds related problems, lemmas, and strategies before attempting a solution.
- **Search system**: explores multiple proof paths instead of relying on a single answer.
- **Checkers**: test generated claims using brute force, algebraic checks, graph checks, number-theoretic checks, SMT/Z3-style checks, and Lean where possible.
- **LLM layer**: uses language models to propose reductions, proof plans, constructions, and candidate lemmas.
- **RLM loop**: records what worked, what failed, and what should be tried next.

The system is designed to behave less like a chatbot and more like a mathematical research assistant with memory, tools, and self-correction.

## What We Are Trying To Build

The aim is to create a proof-search engine that can take a difficult mathematical problem and repeatedly attempt to make progress on it.

At first, the system will work on solved problems. This lets us test whether it can rediscover known solutions without seeing them directly.

Once the harness becomes reliable on solved examples, the same process can be applied to harder unsolved or partially solved problems.

The development path is:

1. Start with solved Erdős-style problems.
2. Hide the known solution from the model.
3. Let the system retrieve related knowledge.
4. Generate proof attempts.
5. Check the attempts using external tools.
6. Compare against the known solution.
7. Store useful discoveries and failure modes.
8. Improve the search loop.
9. Move toward harder open problems.

This is not expected to solve famous open problems immediately. The point is to build the machinery needed for serious automated mathematical experimentation.

## Philosophy

Ingenuity Engine is based on a few guiding principles.

### 1. Retrieval before generation

A model should not reason in isolation. It should first search for nearby solved problems, known lemmas, standard constructions, and previous failed attempts.

### 2. Many weak attempts beat one confident answer

A single proof attempt from an LLM is usually fragile. The system should generate many possible routes, rank them, test them, and keep only what survives.

### 3. Failed attempts are valuable data

Failures should not be thrown away. A failed proof can teach the system which lemmas were insufficient, which reductions were invalid, and which counterexamples block a path.

### 4. Verification matters

Mathematics needs checking. Whenever possible, claims should be tested through brute force, symbolic tools, formal systems, or proof assistants.

### 5. Creativity can be searched

Mathematical creativity often comes from adding the right object, changing the representation, finding the right analogy, or importing a lemma from a nearby field. The system should search over these creative moves instead of waiting for them to appear magically.

## Current Scope

The current version focuses on building the core engine for:

- representing mathematical problems,
- storing lemmas and proof moves,
- retrieving relevant knowledge,
- generating structured proof attempts,
- running basic checkers,
- recording failures,
- and producing readable reports.

The system is still experimental. It is not a finished theorem prover, and it should not be trusted as a source of verified mathematics unless an external checker or formal proof confirms the result.

## Target Use Cases

Ingenuity Engine is meant for experiments such as:

- rediscovering solutions to known Erdős problems,
- comparing different proof-search strategies,
- testing whether retrieval improves mathematical reasoning,
- building a reusable database of proof moves,
- generating candidate lemmas,
- finding counterexamples to weak claims,
- formalizing small parts of informal proofs,
- and studying how LLMs can be combined with symbolic tools.

## Long-Term Vision

The long-term vision is to build a system that can participate in mathematical discovery.

Not by replacing mathematicians, but by acting as a tireless research engine:

- searching known literature,
- trying many approaches,
- checking edge cases,
- finding analogies,
- proposing lemmas,
- building proof sketches,
- and remembering every useful failure.

In the ideal version, the system becomes a loop:

```text
problem → retrieval → proof attempt → checking → failure/success → memory → better attempt
