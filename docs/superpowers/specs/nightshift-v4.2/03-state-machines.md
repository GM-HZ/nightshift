# 03. State Machines

## Purpose

This document defines state transitions for:

- `IssueState`
- `AttemptState`
- `DeliveryState`
- `RunState`

NightShift must treat these as separate state domains.

## IssueState

Suggested states:

- `draft`
- `ready`
- `running`
- `blocked`
- `deferred`
- `done`

### Transition Rules

- `draft -> ready`
  Issue has been normalized and approved.
- `ready -> running`
  Orchestrator selects the issue for execution.
- `ready -> deferred`
  Issue is intentionally postponed.
- `ready -> blocked`
  Pre-admission or preflight reveals a blocker.
- `running -> blocked`
  Execution cannot continue without external change.
- `running -> deferred`
  Execution is paused for queue or budget reasons.
- `running -> done`
  An accepted result has been completed and no further work is required.
- `blocked -> ready`
  The blocker was cleared.
- `deferred -> ready`
  The issue returns to the queue.

## AttemptState

Suggested states:

- `pending`
- `preflight_failed`
- `executing`
- `validating`
- `retryable`
- `accepted`
- `rejected`
- `aborted`

### Transition Rules

- `pending -> preflight_failed`
  Environment or workspace checks fail.
- `pending -> executing`
  Engine invocation starts.
- `executing -> validating`
  Engine finishes with a usable outcome.
- `executing -> retryable`
  Engine outcome is recoverable but not acceptable yet.
- `executing -> aborted`
  Invocation is interrupted or unrecoverably broken.
- `validating -> accepted`
  Required validation passes.
- `validating -> rejected`
  Validation fails and retention is not allowed.
- `validating -> retryable`
  Failure is local and recoverable within budget.

## DeliveryState

Suggested states:

- `none`
- `branch_ready`
- `pr_opened`
- `reviewed`
- `merged`
- `closed_without_merge`

### Transition Rules

- `none -> branch_ready`
  Accepted branch exists and is ready for review.
- `branch_ready -> pr_opened`
  PR was created.
- `pr_opened -> reviewed`
  Human review occurred.
- `reviewed -> merged`
  Result was merged.
- `reviewed -> closed_without_merge`
  Result was intentionally discarded.

## RunState

Suggested states:

- `initializing`
- `running`
- `stopping`
- `completed`
- `aborted`

### Transition Rules

- `initializing -> running`
  Run setup succeeded.
- `running -> stopping`
  Explicit stop requested or graceful shutdown begins.
- `running -> completed`
  Queue exhausted within policy.
- `running -> aborted`
  Fatal condition or unrecoverable system failure.
- `stopping -> completed`
  Graceful stop finished cleanly.

## Composition Rules

These domains interact, but they must not collapse into one status field.

Examples:

- `IssueState=blocked`, `AttemptState=rejected`, `DeliveryState=none`
  Means an issue is blocked after a rejected attempt and nothing is reviewable.

- `IssueState=done`, `AttemptState=accepted`, `DeliveryState=pr_opened`
  Means the issue is complete from the execution perspective and already has a PR.

- `IssueState=deferred`, `AttemptState=retryable`, `DeliveryState=none`
  Means the issue could continue later, but the harness intentionally postponed it.

## Blocker And Progress Coupling

These are not state domains, but they refine state meaning.

- `blocker_type`
  Explains why `IssueState=blocked`.
- `progress_type`
  Explains whether the latest attempt yielded acceptance progress, diagnostic progress, or no progress.

## Event Types

The append-only event log should at least support:

- `issue_created`
- `issue_approved`
- `issue_selected`
- `workspace_prepared`
- `preflight_failed`
- `attempt_started`
- `engine_outcome_recorded`
- `validation_passed`
- `validation_failed`
- `attempt_rejected`
- `attempt_accepted`
- `issue_blocked`
- `issue_deferred`
- `branch_ready`
- `pr_opened`
- `run_completed`
- `run_aborted`

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
