# 06. CLI, Config, Persistence, And Alerting

## Purpose

This document defines the operator-facing control surface and the persistence model required for unattended runs.

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

Suggested layout:

```text
nightshift/
  config.yaml
  issues/
    123.yaml
    241.yaml
  engines/
    codex.md
    claude_code.md
nightshift-data/
  runs/
    <run-id>/
      run-state.json
      events.ndjson
      report.md
      issues/
        <issue-id>.json
        attempts/
          <attempt-id>.json
.nightshift/
  worktrees/
    issue-123/
    issue-241/
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

Reports are for review and traceability. They are not a substitute for alerts.
