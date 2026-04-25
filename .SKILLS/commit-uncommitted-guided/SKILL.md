---
name: commit-uncommitted-guided
description: Surfaces all uncommitted changes in the repo, groups paths (e.g. by top-level directory), and stages/commits in batches the user selects with clear messages. Use when the user wants to commit everything that is not committed, clean up a dirty working tree, split work into logical commits, or asks to add/commit all pending files without a single monolithic commit.
---

# Guided commit for uncommitted work

## When to use

Apply this skill when the user wants to **commit work that is not yet committed**, especially when they want **control over batching** instead of one giant `git add -A` + single commit.

## Workflow

1. **Inspect state** (repo root):
   - `git status`
   - Optionally `git diff` (unstaged) and `git diff --cached` (staged) if the change set is unclear or large.

2. **Group paths for the user**:
   - Prefer **top-level groups** under the repo root (e.g. `experiments/exp97_tier1_quant/`, `edge_inspection/`, root-level files together).
   - If one directory is huge, subdivide (e.g. `experiments/exp97_tier1_quant/results_*` vs scripts).
   - List **untracked**, **modified**, and **deleted** paths explicitly so nothing is hidden.

3. **Let the user choose batches**:
   - Present groups as numbered options (and “all in one commit” only if they ask).
   - For each chosen batch: propose a **short conventional message** (e.g. `feat(exp97): …`, `chore: …`) and confirm or adjust with the user.

4. **Execute per batch** (after confirmation):
   - `git add -- <paths…>` (pathspec list for that batch only).
   - `git commit -m "<message>"`
   - Repeat until the selected batches are done or the user stops.

5. **Verify**:
   - `git status` should show only what the user intentionally left out.

## Safety and conventions

- **Do not** `git add` ignored junk (build artifacts, secrets, huge binaries) without calling it out; if something looks generated, ask before committing.
- **Do not** `--force` push, hard reset, or rewrite history unless the user explicitly requests it.
- Prefer **meaningful commit messages**; avoid messages like `wip` unless the user insists.
- If pre-commit hooks fail, show the hook output and fix or surface the issue—do not bypass hooks unless the user explicitly asks.

## Quick reference

```bash
git status
git add -- path/to/a path/to/b
git commit -m "type(scope): summary"
```

Use `git add -p` only when the user wants to split hunks inside files; default to **path-level** batching to match this skill.
