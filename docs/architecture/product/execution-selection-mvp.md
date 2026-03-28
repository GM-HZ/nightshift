# NightShift Product MVP: Execution Selection

## Purpose

This document defines the next product-layer slice after minimal GitHub issue ingestion.

The goal is to let operators move from:

- admitted local issues existing in the repository

to:

- deliberate execution of a selected set of issues
- or execution of every schedulable admitted issue

without changing the verified kernel semantics.

## Scope

This MVP covers:

- selecting local admitted issues by explicit id list
- selecting all local schedulable issues
- running them one at a time through the existing kernel `run-one` path
- emitting a summary of successes and failures for the batch

Current implementation status in this repository:

- implemented: explicit selection via `run --issues`
- implemented: schedulable selection via `run --all`
- implemented: sequential fail-fast batch runner
- implemented: immediate CLI batch summary
- not yet implemented: daemon mode, continue-on-failure, concurrency, stop/resume

This MVP does not cover:

- daemon mode
- unattended overnight scheduling policy
- concurrency
- stop / pause / resume for multi-issue runs
- delivery automation
- notification fanout

## Design Position Relative To V4.2.1

This slice remains outside the stable kernel boundary.

It reuses the kernel as-is:

- `Issue Registry` remains the source for current schedulable local issues
- `Run Orchestrator.run_one()` remains the execution primitive
- `Validation Gate`, persistence, and recovery semantics remain unchanged

What changes here is orchestration at the product layer:

- choosing which already-admitted local issues to run
- sequencing them
- summarizing the batch result for an operator

## Product Flow

The product-layer flow is:

`local admitted issues -> selection gate -> sequential run-one loop -> batch summary`

Two operator entry points are supported:

- `nightshift run --issues <id1,id2,...>`
- `nightshift run --all`

## Input Contract

This slice consumes local issues that already exist as:

- immutable `IssueContract`
- current `IssueRecord`

It does not fetch GitHub issues directly and does not perform admission itself.

That remains the responsibility of:

- `issue ingest-github`
- future splitter/proposal workflow

## Selection Gate

Before any execution starts, the product layer must build a concrete batch.

### `run --issues`

For explicit issue selection:

- every requested `issue_id` must exist
- every requested issue must currently be schedulable
- duplicates must be removed while preserving left-to-right operator intent

If any requested issue is missing or non-schedulable:

- fail closed before starting the batch
- do not partially start earlier issues

This keeps operator intent precise and auditable.

### `run --all`

For automatic selection:

- read current schedulable issues from `Issue Registry`
- preserve the registry's canonical ordering
- if no issues are schedulable, exit cleanly with an empty-run message

## Execution Model

This MVP uses strictly sequential execution:

- resolve the batch once up front
- run one issue at a time
- each issue execution delegates to the existing `run-one` kernel path

This avoids inventing new multi-issue state semantics before they are needed.

## Failure Policy

The first batch version should support one simple operator policy:

- `fail_fast=true`

Behavior:

- if any issue returns rejected/aborted/failure from `run-one`
- stop the batch immediately
- print a summary of completed vs failed issues

Why start here:

- it is easier to reason about
- it aligns with the current kernel's strong fail-closed semantics
- it avoids silently plowing through a broken overnight environment

Future policy may add:

- `continue_on_failure`

but that is not required for this slice.

## CLI Surface

Recommended commands:

```bash
nightshift run --issues GH-1,GH-2,GH-3 --config /path/to/nightshift.yaml
nightshift run --all --config /path/to/nightshift.yaml
```

Recommended behavior:

- resolve repo from `--repo` or `project.repo_path`
- print selected issue ids before execution
- print per-issue result lines as each `run-one` finishes
- print one final batch summary

## Summary Shape

The first version only needs a small operator-friendly summary:

- batch size
- issues attempted
- issues accepted
- first failure issue id, if any
- whether execution stopped early

This does not replace historical run reporting.

It is only the immediate operator-facing batch result.

## Relationship To Queue State

This slice should not create a second queue model.

It should use the existing current issue state:

- `issue_state=ready`
- `attempt_state=pending`

The queue ordering for `run --all` must remain the registry's canonical schedulable ordering.

Manual `queue reprioritize` must therefore affect future `run --all` selection without any extra sync.

## Failure Modes

Expected fail-closed classes:

- requested issue id does not exist
- requested issue is not schedulable
- duplicate issue ids collapse into one effective selection
- no schedulable issues for `run --all`
- any underlying `run-one` execution failure

These should produce explicit operator output instead of silent skipping.

## Phase Boundary

This slice is still product workflow, not kernel.

It should be implemented above the kernel and depend on:

- config loading
- issue registry selection
- the existing `run-one` primitive

It should not:

- add new run-state persistence for batch orchestration in the first version
- alter kernel acceptance/recovery semantics
- alter validation behavior

## Non-Goals For This Slice

- overnight daemon loop
- cron-style scheduling
- concurrency or slots
- automatic retry policy for batches
- GitHub delivery / PR creation
- alert routing

Those remain future product-workflow slices.
