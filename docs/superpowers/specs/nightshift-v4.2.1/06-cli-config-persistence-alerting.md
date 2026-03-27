# 06. CLI, Config, Persistence, And Alerting

## Purpose

This document defines the V4.2.1 operator-facing control surface and the persistence model required for unattended runs.

V4.2.1 mainly tightens:

- the storage home of the current `IssueRecord`
- the meaning of queue reprioritization
- the uniqueness and usage of `run_id`

## CLI Groups

### Preparation

- `nightshift split --requirement '...' --repo /path/to/repo`
- `nightshift split --file requirement.md --repo /path/to/repo`

### Queue And Execution

- `nightshift queue status`
- `nightshift queue show <id>`
- `nightshift queue add <path>`
- `nightshift queue reprioritize <id>`
- `nightshift run --repo /path/to/repo`
- `nightshift run --repo /path/to/repo --daemon`
- `nightshift run-one <id> --repo /path/to/repo`
- `nightshift stop`

### Reports And Diagnostics

- `nightshift report`
- `nightshift report --run <run-id>`
- `nightshift logs --issue <id>`
- `nightshift recover --run <run-id>`

## Command Semantics Tightening

### `queue reprioritize`

`nightshift queue reprioritize <id>` updates:

- `IssueRecord.queue_priority`

It must not update:

- `IssueContract.priority`

### `queue show`

`nightshift queue show <id>` should display:

- contract `priority`
- current `queue_priority`
- current `issue_state`
- latest `attempt_state`
- latest `delivery_state`

### `recover --run`

`nightshift recover --run <run-id>` must target the exact unique `run_id`.

A date string alone is not a valid `run_id`.

Operational rule:

- the supplied `run_id` is the interrupted source run
- recovery records the source run as interrupted or aborted as needed
- recovery creates a new controlling run with a new `run_id`
- the command should surface the new recovery run id clearly

## Config Model

Suggested `nightshift.yaml` sections:

- `project`
  - repo path
  - main branch

- `runner`
  - default engine
  - fallback engine
  - issue timeout
  - total overnight timeout

- `validation`
  - static validation commands
  - core regression commands
  - promotion commands

- `issue_defaults`
  - default priority
  - default forbidden paths
  - default test edit policy
  - default attempt limits
  - default timeouts

- `retry`
  - max retries
  - retry policy
  - failure circuit breaker

- `workspace`
  - worktree root
  - artifact root
  - cleanup whitelist

- `alerts`
  - enabled channels
  - severity thresholds

- `report`
  - output directory
  - summary verbosity

## Persistence Layout

Recommended layout:

```text
nightshift/
  config.yaml
  issues/
    <issue_id>.yaml
  engines/
    codex.md
    claude_code.md
nightshift-data/
  issue-records/
    <issue_id>.json
  active-run.json
  alerts.ndjson
  runs/
    <run_id>/
      run-state.json
      events.ndjson
      report.md
      issues/
        <issue_id>.json
      attempts/
        <attempt_id>.json
      artifacts/
        attempts/
          <attempt_id>/
.nightshift/
  worktrees/
    issue-<issue_id>/
```

## Persistence Rules

- `nightshift/issues/<issue_id>.yaml`
  Immutable `IssueContract`
- `nightshift-data/issue-records/<issue_id>.json`
  Authoritative current `IssueRecord`
- `nightshift-data/runs/<run_id>/run-state.json`
  Authoritative `RunState` for that run
- `nightshift-data/runs/<run_id>/attempts/<attempt_id>.json`
  Authoritative `AttemptRecord` for that run
- `nightshift-data/runs/<run_id>/artifacts/attempts/<attempt_id>/`
  Attempt-local execution artifacts referenced by `AttemptRecord.artifact_dir`
- `nightshift-data/runs/<run_id>/events.ndjson`
  Append-only event history for that run
- `nightshift-data/alerts.ndjson`
  Append-only alert history across runs

The issue snapshots stored under `nightshift-data/runs/<run_id>/issues/` are denormalized run artifacts for reporting and auditability.

They are not the source of truth for current issue state after the run completes.

They are, however, the preferred issue-level source for historical run reports tied to that exact `run_id`.

## Run Id Rule

`run_id` must be globally unique and should be human-readable.

Recommended format:

```text
run-<UTC timestamp>-<short unique suffix>
```

Example:

```text
run-20260327T140500Z-01JQ8J7M6Q0P
```

The run directory must use the exact `run_id` string:

```text
nightshift-data/runs/<run_id>/
```

## Snapshot Vs Event Log

MVP should maintain both:

- current state snapshots
- append-only event history

Current state powers live orchestration.
Event history powers:

- recovery
- audits
- reporting
- future analytics

## Alerting Semantics

Critical alerts should fire on:

- run aborted unexpectedly
- global timeout reached
- circuit breaker triggered
- environment failure blocks the entire queue
- state store corruption or recovery failure
- repeated engine crashes across issues

Warning alerts should fire on:

- issue blocked
- retry budget exhausted on one issue
- engine fallback activated
- flaky validation patterns

## Report Responsibilities

Reports should summarize:

- run duration
- issues accepted
- issues blocked
- issues deferred
- retry distribution
- engine usage
- links to artifacts and PRs

Historical run reports must be generated from the targeted run's persisted history:

- `run-state.json`
- run-scoped issue snapshots
- attempt records
- events
- alerts

They must not be regenerated from current live `IssueRecord` snapshots alone.

Reports are for review and traceability. They are not a substitute for alerts.
