# Ingenuity Engine: A Paused/Failed Attempt at LLM-Driven Math Research

I am open-sourcing this repository as a postmortem.

I started Ingenuity Engine to test a specific bet: if I combined LLM creativity with strict verification and persistent memory, I could build a system that makes real progress on hard Erdős-style math problems.

I built a lot. I learned a lot. I did not achieve the core goal.

This project is paused and I consider it a failed attempt at the original objective.

## How This Started

My initial assumptions were:

1. LLMs are creative but unreliable for rigorous math.
2. Formal tools (Lean) are reliable but difficult to use directly at scale.
3. A good orchestrator might combine both: LLM for ideas, formal checks for truth.

So I built around a loop, not a one-shot answer:

```text
problem -> retrieve context -> generate candidate moves -> verify/reject -> store failures -> retry
```

I targeted hard number-theoretic search around Erdős-style statements, with `erdos_004` as the main stress test.

## What I Actually Built

Most implementation lives in `erdos-engine/`:

- A local CLI harness (`run`, `report`, `list-problems`, `sanity-check-path`, and bootstrap commands).
- Beam search over research states (not just one-shot generations).
- Retrieval from a lemma store, theorem graph, and persistent failure memory.
- A Lean-first checking path with preflight and formalization attempts.
- Optional critic model pass and optional secondary heuristic checkers.
- An RLM-style fallback mode intended to recover from stall states.
- Persistent artifacts for every run in `attempts_erdos/...` plus reports in `erdos-engine/reports/...`.

In plain terms: this was not just a concept note. I built and ran a full experiment harness.

## Models and Providers I Used

Runs in this repo used OpenRouter-compatible endpoints with combinations such as:

- `x-ai/grok-4.1-fast` (proposer in scripted runs),
- `google/gemini-3.1-flash-lite-preview` (critic/confirmation in scripted runs),
- `openai/gpt-oss-20b:free` (default proposer in config),
- `google/gemini-2.5-flash-lite` (default critic in config).

The key point: this was not one model failing. The orchestration as a whole failed to produce reliable formal progress on the target problem.

## Timeline: What I Tried, In Order

### Phase 1: Build the spine

I first built storage, retrieval, run orchestration, and reporting so I could iterate quickly without losing history. This phase mostly worked.

### Phase 2: Make checking first-class

I wired Lean preflight and Lean-first evaluation into the core loop, then added secondary checks behind it. This improved honesty: fewer fake wins, more explicit failures.

### Phase 3: Add search and recovery

I layered beam search, stricter move parsing, critic paths, and RLM fallback to avoid getting trapped in one bad generation stream.

### Phase 4: Run many attempts on `erdos_004`

I ran repeated experiments (see the timestamped attempt directories under `attempts_erdos/erdos_004/` and reports under `erdos-engine/reports/`).

This is where the project broke:

- many runs completed cleanly from an infrastructure perspective,
- but accepted formal progress stayed near zero,
- and final run status repeatedly ended as `stalled`.

At that point, I had to call the project what it was: a good research harness that failed at its primary math objective.

## Iteration Breakdown (Cases, Specs, Learnings)

The table below summarizes the main iteration clusters I ran, using commit history plus representative run reports from `attempts_erdos/erdos_004/`.

| Iteration case | Representative runs | Specs (what I changed) | Expected outcome | Actual outcome | Advantage | Disadvantage | What I learned |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Calibration and smoke setup | `20260425_192741_calibration`, `20260425_210221_smoke_case_rlm` | Verified harness wiring, Lean preflight, minimal search configs, baseline RLM on | Confirm pipeline integrity and establish first positive signal | Got `plausible_progress` signals and stable traces, but with low-realism accepted claims | Fast feedback, good for debugging system glue | Early "progress" metrics were easy to game and not tightly coupled to true theorem progress | Infrastructure can look healthy while math progress is still fake/weak |
| Early model pairing (DeepSeek/Gemini-lite style runs) | `20260425_194839_deepseek_v4_flash`, `20260425_202605_deepseek_plus_gemini31lite` | Swapped proposer/critic combinations and prompt styles; kept retrieval + Lean-first checks | Better move quality from model diversity | Produced cleaner candidate skeletons and some verified intermediate artifacts, but no end-to-end proof | Broader idea diversity and better wording of steps | More model variation increased operational complexity without breakthrough | Model swaps alone do not solve the language-to-formal bottleneck |
| Retry storm: parser/prompt/timeout patches | `20260425_213225_stall_patch_probe` through `20260425_215508_solve4_retry_with_fallback_logging` | Repeated retries with JSON parsing fixes, timeout tuning, content patches, fallback logging | Break out of stall loops and convert more moves to valid formal steps | Mostly local improvements; still no robust theorem-level advancement | Rapid iteration exposed brittle points quickly | High churn created "activity noise" and made genuine progress hard to distinguish | Tight parser policies are necessary but not sufficient for deep math progress |
| Depth/beam and graph-focus expansions | `20260425_220809_solve4_depth100`, `20260425_224539_solve4_graph_focus_depth100`, `20260425_230403_solve4_graph_focus_solo` | Increased search depth/beam variants, graph-focused retrieval, solo graph-focused tests | More search budget should find novel viable paths | More logs and candidate moves, but repeated pattern families and persistent stalls | Better coverage of search space and clearer failure signatures | Compute budget mostly amplified repeated low-value branches | More search without stronger guidance mainly scales repetition |
| Lean/policy hardening and no-secondary checks | `20260425_220434_solve4_lean600_no_secondary`, `20260425_230656_solve4_grok411_20260425_230651` | Lean timeout/policy changes, secondary-checker toggles, stricter acceptance pressure | Reduce false positives and force cleaner formal path | Integrity improved, but accepted-claim count did not translate to final theorem progress | Better honesty and lower risk of fake wins | Stricter gates also reduce apparent momentum | Verification strictness is correct, but it exposes missing constructive proof machinery |
| Curriculum decomposition (reduction/covering/bridge) | `20260426_192035_curriculum_reduction_20260427_0050`, `20260426_192117_curriculum_covering_20260427_0050`, `20260426_192207_curriculum_bridge_20260427_0050` | Split objective into milestones (gap reduction, CRT covering, parameter growth bridge) | Modular subgoals should compound into full proof progress | In representative reports, runs still returned `stalled` with empty accepted claims | Correct decomposition strategy in theory | Subgoal interfaces remained too loose to force compositional progress | Curriculum needs stricter contracts between subgoals, not just renamed milestones |
| Final hardening retries and verification reruns | `20260426_195042_retry_after_fallback_fix_20260427_0119` through `20260426_210429_retry_after_prompt_hardening_20260427_0234` | Prompt hardening, fallback fixes, obligation overwrite fixes, timeout policy tweaks, verification reruns | Last-mile stabilization should recover usable path | Representative final reports stayed at `stalled`, depth 0, no accepted claims | Produced definitive evidence that failure was structural, not one-off | Consumed effort without objective movement | The failure mode was architectural: orchestration quality exceeded mathematical proof capability |

### Cross-Iteration Pattern

Across these cases, the same pattern repeated:

1. I improved infrastructure reliability.
2. I improved trace quality and observability.
3. I improved filtering against bad model output.
4. I did **not** improve conversion of candidate reasoning into durable formal theorem progress.

That is the core reason this is marked as a failed attempt rather than an unfinished success.

## What Worked

- **End-to-end execution worked.** Retrieval, generation, evaluation, and report writing ran repeatedly.
- **Lean setup was operationally reliable.** Toolchain preflight/build checks were consistently successful in recorded runs.
- **Observability was strong.** I captured logs, events, best-state snapshots, and markdown/json reports suitable for deep failure analysis.
- **Iteration got fast.** I could change prompts/policies/parsers and re-run quickly.

These are engineering wins, not theorem-proving wins.

## Where It Failed

- **Primary objective failed:** I did not get a verified solution path for the hard target problem.
- **Progress repeatedly collapsed:** runs ended `stalled` with empty accepted-claim sets and little effective depth gain.
- **Recovery logic underperformed:** fallback/reflection often produced activity, not durable formal progress.
- **Language-to-formal bridge was the bottleneck:** plausible text still failed to become Lean-usable steps.

Bottom line: I generated lots of attempts and artifacts, but not mathematically meaningful formal advancement on the target.

## Assumptions: What I Got Right vs Wrong

### What I got right

- **"Never trust raw model output."** Mandatory structure and checking prevented self-deception.
- **Failure memory matters.** Persistent traces made iteration scientific instead of anecdotal.
- **Lean-first was the right guardrail.** Without it, I would likely have mistaken fluent text for real progress.

### What I got wrong

- **I overestimated orchestration.** Retrieval + beam search + critic loops did not automatically produce deep mathematical insight.
- **I overestimated compounding from raw iteration.** More attempts often meant more repetition, not better ideas.
- **I underestimated formalization cost.** Translating informal strategy into formalizable steps was harder than almost everything else.
- **I started too hard, too soon.** The system needed a much stronger solved-problem curriculum before serious open-problem-style targets.

## Brutal Bottom Line

I put real effort into building this stack, and it still failed its central claim.

That failure is exactly why this repo is public: it is a concrete, inspectable record of where this style of LLM-plus-orchestration currently breaks on hard, formalizable mathematics.

## What This Repo Is Useful For Now

- Studying an LLM + retrieval + checker architecture in one place.
- Mining failure traces for better future search policies.
- Benchmarking "looks-smart" outputs against formal verification pressure.
- Understanding practical bottlenecks in moving from language reasoning to proof-grade steps.

## Current Status

Paused. Archived. Open-sourced for transparency.

If I resume this line of work, I should restart with:

- tighter solved-problem curricula,
- narrower formal subgoals per step,
- stronger lemma grounding before generation,
- and stricter acceptance criteria for what counts as progress.
