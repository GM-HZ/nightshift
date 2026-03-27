# 03. State Machines

## Purpose

V4.2.1 inherits the V4.2 state machine design and adds the missing recovery rules for in-flight attempts after crash or restart.

Base source:

- [../nightshift-v4.2/03-state-machines.md](../nightshift-v4.2/03-state-machines.md)

Where this document adds rules, it supersedes the V4.2 text.

## Base State Domains

The base state domains remain unchanged:

- `IssueState`
- `AttemptState`
- `DeliveryState`
- `RunState`

## Recovery Normalization Rule

After crash or restart, NightShift must not leave runtime records in ambiguous in-flight states indefinitely.

The Orchestrator must reconcile the prior active run and any in-flight attempt into a durable post-recovery state before resuming queue execution.

### Attempt Recovery Rules

If the latest attempt was persisted as:

- `pending`
  The attempt may remain `pending` only if no engine invocation was started.
- `executing`
  The attempt must be reconciled immediately during recovery.
- `validating`
  The attempt must be reconciled immediately during recovery.

### `executing` Recovery Resolution

If an attempt was last seen as `executing`, recovery must resolve it as follows:

1. If the engine invocation is confirmed live and resumable under adapter capabilities, the attempt may remain active and continue under orchestrator control.
2. If a durable normalized `EngineOutcome` already exists, transition the attempt to `validating` and continue validation.
3. If no durable usable outcome exists, transition the attempt to `aborted`.

Operational rule:

- MVP should not assume step 1 is available.
- The safe default is step 2 when artifacts are sufficient, otherwise step 3.

### `validating` Recovery Resolution

If an attempt was last seen as `validating`, recovery must not trust partial in-memory validation progress.

Instead:

1. reload the attempt record and artifacts
2. rerun validation from the start
3. transition to `accepted`, `rejected`, or `retryable` based on the rerun result

### Issue Recovery Rules

If an issue was last seen as `running`, recovery must not leave it as `running` after reconciliation.

After reconciling the latest attempt:

- `accepted` attempt -> issue becomes `done`
- `retryable` attempt -> issue becomes `ready` or `deferred` according to policy
- `aborted` or repeated semantic failure -> issue becomes `blocked` or `ready` according to policy
- `rejected` attempt with no immediate retry -> issue becomes `blocked` or `deferred` according to policy

### Run Recovery Rules

If a process crashed while `RunState=running`, that run should be treated as interrupted.

Recommended recovery behavior:

1. mark the interrupted run as `aborted` with a recovery event
2. reconcile active issue and attempt state
3. create a new controlling recovery run with a new `run_id`

This keeps `run_id` semantics clean and avoids pretending one uninterrupted run survived a process crash.

Operational consequence:

- the interrupted run remains the source run for audit and historical reporting
- the recovery run is a new run that may continue the remaining queue

## Additional Event Types

The append-only event log should additionally support:

- `run_recovery_started`
- `run_recovery_completed`
- `attempt_recovered`
- `attempt_aborted_on_recovery`
- `validation_restarted`

## Recovery Rule

After a crash or restart, NightShift should reconstruct:

- current `RunState`
- current `IssueState`
- latest `AttemptState`
- latest `DeliveryState`

from:

- current state snapshots first
- append-only event history second

The event log exists to make replay and diagnosis possible even if snapshot repair is needed.
