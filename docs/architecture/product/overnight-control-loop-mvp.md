# Overnight Control Loop MVP

## Purpose

This document defines the smallest unattended overnight control layer that fits:

- the current live NightShift repository surface
- the `v4.2.1` kernel and run-state model
- the current product-side queue admission and frozen-contract workflow

It is intentionally narrower than the full historical `v4.2.1` daemon vision.

The goal is to restore a governed overnight loop without forcing:

- dependency-aware scheduling
- parallel slot scheduling
- notification delivery
- rich morning reporting
- delivery automation coupling

Those remain separate follow-on concerns.

---

## Why This Exists

NightShift now has these live building blocks:

- `issue ingest-github`
- execution work orders
- `queue add`
- frozen `IssueContract`
- `run --issues`
- `run --all`
- `deliver --issues`
- `recover`
- `report`

That is enough for operator-invoked batch execution, but it is still not a true unattended overnight loop.

The missing layer is a control surface that can:

- start an unattended execution window
- keep selecting the next schedulable issue
- stop cleanly
- surface whether the loop finished, stopped, or aborted

This document defines that layer.

---

## Alignment With `v4.2.1`

This MVP remains aligned with `v4.2.1`:

- the stable kernel still owns execution, validation, persistence, and recovery
- product workflow still owns the overnight control surface
- `RunState` remains the authoritative top-level runtime object
- the queue remains the source of truth for what is schedulable

This is a product-side orchestration refinement, not a kernel redesign.

---

## Scope

### In Scope

- one explicit overnight control command surface
- unattended sequential execution
- stop request handling
- explicit loop-level run state
- loop summary and minimal operator visibility
- compatibility with `queue add` and frozen contracts

### Out Of Scope

- dependency-aware scheduling
- slot-aware or parallel scheduling
- continue-on-failure policy variants
- automatic delivery after acceptance
- notification delivery
- rich report generation
- multi-repo coordination
- automatic planning-entry behavior

---

## Design Principle

The overnight control loop should be a thin governed layer above the current product-facing run surface.

It should not replace `run-one` or the existing batch execution service.

It should:

- reuse current schedulable ordering
- reuse `RunOrchestrator.run_one()`
- introduce one loop-level control state
- remain conservative and observable

This means the first loop is intentionally:

- sequential
- single-repo
- fail-fast
- explicit-stop-aware

---

## Operator Surface

The MVP control surface is:

- `nightshift run --all --daemon`
- `nightshift stop`

### Meaning Of `run --all --daemon`

This command:

- starts an unattended loop run for the current repository
- repeatedly selects the next schedulable issue
- executes it using existing frozen-contract semantics
- stops when:
  - no schedulable issues remain
  - a stop request is observed
  - one issue fails and fail-fast ends the loop

### Meaning Of `stop`

This command:

- targets the currently active daemon-controlled run for the repository
- records a stop request
- does not kill an in-flight engine subprocess abruptly
- causes the loop to stop after the current issue finishes or aborts

This keeps stop behavior conservative and compatible with current execution semantics.

---

## Loop State Model

The loop uses the existing `RunState` object and extends interpretation rather than inventing a second top-level state object.

### `RunState` Usage

Loop runs continue to use:

- `run_id`
- `run_state`
- `started_at`
- `ended_at`
- `issues_attempted`
- `issues_completed`
- `active_issue_id`
- `active_attempt_id`
- `active_worktrees`

### Additional Loop Metadata

The loop should add a small amount of loop-level metadata to persisted run state:

- `selected_engine_policy`
  Existing field can continue to describe the effective engine policy.
- `base_branch`
  Existing field continues to describe repository baseline.

The loop should also record product-side loop metadata under the run directory, for example:

- `loop-mode = daemon`
- `fail-fast = true`
- `stop-requested = false|true`
- `stopped_reason = user_stop | failure | drained | none`

This can live in a dedicated small JSON metadata file alongside `run-state.json` rather than bloating the kernel model immediately.

---

## State Transitions

The MVP daemon loop uses these run outcomes:

- `running`
- `stopping`
- `completed`
- `aborted`

### Start

When the daemon loop starts:

- create a new controlling `run_id`
- persist run state as `running`
- mark loop metadata `loop-mode=daemon`

### Stop Requested

When `nightshift stop` is called:

- the current daemon loop metadata is updated with `stop-requested=true`
- the run state moves to `stopping`
- no new issue is selected after the current issue completes

### Drained

When the queue has no schedulable issues left:

- the run ends as `completed`
- loop metadata records `stopped_reason=drained`

### Failed

When one issue fails in fail-fast mode:

- the loop stops immediately after that issue result is persisted
- the controlling run ends as `aborted`
- loop metadata records `stopped_reason=failure`

### User Stop

When a stop is requested and the current issue finishes:

- the controlling run ends as `completed`
- loop metadata records `stopped_reason=user_stop`

This treats a graceful user stop as a controlled finish, not an abnormal abort.

---

## Selection Semantics

The daemon loop does not invent a new scheduler.

It must reuse the current live selection semantics:

- only issues already admitted via `queue add`
- only issues with frozen contracts
- current `IssueRegistry.list_schedulable_records()` ordering

This keeps queue admission as the sole execution admission point.

---

## Failure Policy

The MVP loop uses only one policy:

- `fail_fast = true`

Behavior:

- accepted issue: continue
- rejected issue: stop loop
- aborted issue: stop loop
- orchestrator exception: stop loop

This is intentionally conservative.

Later policy variants such as continue-on-failure should be added only after this baseline is stable.

---

## Recovery Relationship

The daemon loop does not replace existing recovery semantics.

If the loop is interrupted unexpectedly:

- the current controlling run remains the interrupted source run
- `recover --run <source_run_id>` continues to create a new controlling run

The loop MVP does not add a dedicated `resume daemon loop` command.

That can come later after stop/pause/resume semantics are stronger.

---

## Persistence Expectations

The daemon loop should persist:

- controlling `RunState`
- append-only run events
- current issue records through normal execution flow
- run issue snapshots through normal execution flow
- loop metadata file for daemon-specific control flags

The daemon loop must not introduce dual state sources for queue admission or current issue state.

---

## Minimal Events

The loop should append a few loop-level events in addition to normal per-issue events:

- `daemon_started`
- `daemon_stop_requested`
- `daemon_drained`
- `daemon_stopped`
- `daemon_failed`

These should reuse the existing `EventRecord` stream.

---

## CLI Behavior

### `nightshift run --all --daemon`

Should:

- reject `--issues`
- require repository config like current `run`
- print the new controlling `run_id`
- run until drained, failed, or stopped
- exit non-zero when the loop aborts on failure

### `nightshift stop`

Should:

- find the active daemon run for the repository
- set `stop-requested=true`
- print a short confirmation
- fail clearly if no daemon run is active

---

## Why This MVP Is The Right Size

This is the smallest useful unattended loop because it:

- builds directly on current live execution code
- preserves queue admission as the only freeze/admission point
- keeps the control model observable
- avoids prematurely coupling loop control with delivery, notifications, or richer scheduling

It restores the product-side overnight control seam without destabilizing the kernel.

---

## Follow-On Work

After this MVP is stable, the next natural expansions are:

1. continue-on-failure policy
2. pause / resume semantics
3. notification hooks
4. richer morning report
5. dependency-aware and slot-aware scheduling

Those should remain separate increments.
