# NightShift Product MVP: Queue Admission

## Purpose

This document defines the product-layer queue-admission slice that sits between:

- intake of external work items

and:

- execution selection through `run --issues` or `run --all`

The goal is to make operator intent explicit without requiring people to manually reason about raw contract paths, current-record files, or implicit local state.

## Scope

This MVP covers:

- turning newly admitted local issues into an explicit queue operation
- a single operator command surface for admitting already-materialized issues
- optional reprioritization at admission time
- clean operator feedback about what entered the queue and why

Current implementation status in this repository:

- implemented: explicit `queue add <issue_id>...`
- implemented: all-or-nothing validation before queue mutation
- implemented: idempotent success for already-admitted `ready + pending`
- implemented: draft materialization path via `issue ingest-github --materialize-only`
- implemented: draft-to-ready normalization during explicit queue admission
- not yet implemented: richer approval policy, batch review UX, or dependency-aware queueing

This MVP does not cover:

- a second queue data model
- hidden scheduling policy
- automatic splitting
- automatic GitHub issue creation
- delivery or PR workflows

## Design Position Relative To Current Product Slices

Current repository status:

- `issue ingest-github` can already materialize an execution-ready `IssueContract` and `IssueRecord`
- `run --issues` and `run --all` can already execute admitted local issues sequentially

What is still awkward is the operator experience around admission:

- today, materialization and queue presence are effectively coupled
- there is no explicit command that says "this issue is now part of tonight's queue"
- queue-related operator actions are split between ingestion, queue inspection, and run selection

This slice addresses that gap.

## Product Flow

The product-layer flow becomes:

`external issue -> ingest -> local admitted issue -> queue add -> queue inspect/reprioritize -> run`

The key idea is:

- ingestion creates a valid local issue
- queue admission makes that issue an explicit part of the operator-managed worklist

## Queue Model

This MVP must not invent a second queue state model.

Queue admission should continue to use the current live issue state:

- `IssueRecord.issue_state`
- `IssueRecord.attempt_state`
- `IssueRecord.queue_priority`

A local issue is considered queue-admitted when:

- the contract exists
- the current issue record exists
- the issue is in a schedulable live state, normally:
  - `issue_state=ready`
  - `attempt_state=pending`

So `queue add` in this slice is not "write into a new queue table".

It is:

- a controlled operator admission action
- plus any necessary live-state normalization into a schedulable queue-visible record

## Why `queue add` Still Matters If Records Already Exist

There are two useful operator modes:

### Mode 1: Coupled Admission

`issue ingest-github` may optionally materialize directly into a schedulable queue-ready issue.

This is what the current MVP effectively does today.

### Mode 2: Explicit Queue Admission

An operator may want to:

- ingest first
- review local materialization
- then explicitly admit one or more issues into tonight's queue

This is the mode `queue add` exists to support.

That means the product rule should be:

- ingestion and queue admission may happen together in the happy path
- but the system must also support explicit queue admission as a separate operator action

## Recommended Queue Admission Semantics

### Input

`queue add` should accept one of:

- one local `issue_id`
- multiple local `issue_id`s

The first version should not use file paths as the primary operator contract.

Why:

- the operator thinks in issue ids, not filesystem paths
- `issue_id` is already the stable identity used by `queue show`, `queue reprioritize`, `run --issues`, and reports

Recommended shape:

```bash
nightshift queue add GH-1
nightshift queue add GH-1 GH-2 GH-3
```

## Admission Gate

`queue add` must verify:

- the immutable `IssueContract` exists
- the current `IssueRecord` exists
- the issue is execution-capable and not malformed
- the issue is not already running/done in a way that makes queue admission nonsensical

### Accepted Initial States

The first version should accept:

- `ready + pending`
- `draft + pending`

This means:

- if an issue is already in the queue-ready state, `queue add` is idempotent
- if an issue is materialized for review in `draft`, `queue add` normalizes it into `ready`

### Rejected States

The first version should reject:

- `running`
- `done`
- `blocked`
- `deferred`

Why:

- these states require a more opinionated workflow policy
- the first queue-admission slice should remain fail-closed

## Priority Handling

The initial rule should be simple:

- if no priority override is provided, keep the existing `IssueRecord.queue_priority`
- if `--priority` is provided, update only `IssueRecord.queue_priority`
- never mutate `IssueContract.priority`

This stays aligned with the current reprioritization semantics.

## Idempotency

`queue add` should be idempotent for already queue-ready issues.

If the issue is already:

- `issue_state=ready`
- `attempt_state=pending`

then the command should:

- succeed
- report that the issue is already admitted
- avoid rewriting unrelated fields

## Relationship To Ingestion

This slice deliberately allows two product UX paths:

### Fast Path

`issue ingest-github`

- provenance pass
- admission pass
- materialize
- optionally mark as queue-admitted immediately

### Review Path

`issue ingest-github --materialize-only`

- provenance pass
- admission pass
- materialize
- do not admit yet

Then later:

`nightshift queue add GH-1`

This is the path that gives operators more control without changing kernel semantics.

## CLI Surface

Recommended commands:

```bash
nightshift queue add GH-1
nightshift queue add GH-1 GH-2 GH-3
nightshift queue add GH-1 --priority urgent
```

Recommended operator output:

- admitted issue ids
- already-admitted issue ids
- rejected issue ids with reasons

The first version should fail closed if any requested issue cannot be admitted.

That means:

- explicit admission should be all-or-nothing
- no partial queue mutation on mixed-validity input

## Failure Modes

Expected fail-closed classes:

- unknown issue id
- missing contract
- missing record
- issue already running
- issue already done
- issue currently blocked or deferred
- invalid priority override

These should all produce explicit operator-facing rejection reasons.

## Relationship To `run --all`

`run --all` should continue to consume:

- the current schedulable local queue

So after this slice lands:

- `queue add` controls admission into that schedulable set
- `queue reprioritize` controls ordering inside that set
- `run --all` consumes that set in canonical order

This keeps the system understandable:

- one live queue
- one ordering mechanism
- one execution selector

## Phase Boundary

This slice remains product workflow, not kernel.

It may depend on:

- `Issue Registry`
- existing live issue states
- current queue inspection commands

It should not:

- add a second queue store
- change kernel run semantics
- invent automatic scheduling policy

## Non-Goals For This Slice

- queue approval workflows
- batch continue-on-failure policy
- daemon loop
- dependency graph scheduling
- automatic delivery / PR creation

Those remain later product-workflow slices.
