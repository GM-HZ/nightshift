# 01. Domain Model

## Purpose

This document defines the core objects that the NightShift kernel must share. These are the common language between:

- Issue Registry
- Run Orchestrator
- Engine Adapter Layer
- Validation Gate
- State Store
- Reporting and notification edge modules

If these objects are not stable, the rest of the system will drift.

## Identifier Model

The system needs stable identifiers for each domain.

- `issue_id`
  Stable identifier for one issue contract.
- `run_id`
  One overnight run.
- `attempt_id`
  One attempt on one issue within one run.
- `engine_invocation_id`
  One concrete CLI invocation.
- `delivery_id`
  Optional identifier for a PR, review artifact, or provider-side object.

Identifiers should be globally unique within their domain and never be repurposed.

## Core Objects

### IssueContract

This is the immutable execution contract approved by a human.

Key fields:

- identity:
  - `issue_id`
  - `title`
  - `kind`
  - `priority`
- product intent:
  - `goal`
  - `description`
  - `acceptance`
  - `notes`
  - `risk`
- execution policy:
  - `engine_preferences`
  - `allowed_paths`
  - `forbidden_paths`
  - `test_edit_policy`
  - `attempt_limits`
  - `timeouts`
- verification:
  - `issue_validation`
  - `static_validation`
  - `regression_validation`
  - `promotion_validation`

Invariants:

- `kind=execution` requires executable validation
- `allowed_paths` must not be empty for execution issues
- `forbidden_paths` may be empty, but must still be explicit

### IssueRecord

This is the mutable runtime record for an issue.

Key fields:

- `issue_id`
- `issue_state`
- `attempt_state`
- `delivery_state`
- `blocker_type`
- `progress_type`
- `current_run_id`
- `latest_attempt_id`
- `accepted_attempt_id`
- `branch_name`
- `worktree_path`
- `retry_count`
- `deferred_reason`
- `last_summary`
- `created_at`
- `updated_at`

Invariants:

- `blocker_type` must be set when `issue_state=blocked`
- `delivery_state != none` requires at least one accepted attempt

### AttemptRecord

This is the full record for one execution attempt.

Key fields:

- identity:
  - `attempt_id`
  - `issue_id`
  - `run_id`
- execution:
  - `engine_name`
  - `engine_invocation_id`
  - `engine_capabilities_snapshot`
  - `attempt_state`
  - `progress_type`
- workspace:
  - `branch_name`
  - `worktree_path`
  - `pre_edit_commit_sha`
- preflight:
  - `preflight_passed`
  - `preflight_summary`
- results:
  - `engine_outcome`
  - `validation_result`
  - `recoverable`
  - `retry_recommended`
  - `summary`
- timestamps:
  - `started_at`
  - `ended_at`
  - `duration_ms`

Invariants:

- `attempt_state=accepted` requires validation pass
- `attempt_state=preflight_failed` requires `preflight_passed=false`

### EngineCapabilities

This is the adapter-declared capability surface of an engine.

Suggested fields:

- `supports_streaming_output`
- `supports_structured_result`
- `supports_patch_artifact`
- `supports_resume`
- `supports_noninteractive_mode`
- `supports_worktree_execution`
- `supports_file_scope_constraints`
- `supports_timeout_enforcement`
- `supports_json_output_hint`

This is used for scheduling and compatibility checks, not for recording one specific invocation result.

### EngineOutcome

This is the normalized result of one engine invocation.

Suggested fields:

- `engine_name`
- `engine_invocation_id`
- `outcome_type`
- `exit_code`
- `recoverable`
- `engine_error_type`
- `summary`
- `stdout_path`
- `stderr_path`
- `artifact_paths`
- `started_at`
- `ended_at`
- `duration_ms`

Supported `outcome_type` values:

- `success`
- `engine_timeout`
- `engine_crash`
- `partial_output`
- `invalid_output`
- `interrupted`
- `environment_error`

### ValidationResult

This is the independent acceptance record produced by the Validation Gate.

Suggested fields:

- `passed`
- `failed_stage`
- `stages`
- `summary`
- `raw_artifact_paths`
- `evaluated_at`

Each stage entry should carry:

- `stage_name`
- `required`
- `passed`
- `skipped`
- `pass_condition`
- `command_results`

### RunState

This is the top-level runtime state for one overnight run.

Suggested fields:

- `run_id`
- `run_state`
- `base_branch`
- `selected_engine_policy`
- `started_at`
- `ended_at`
- `issues_attempted`
- `issues_completed`
- `issues_blocked`
- `issues_deferred`
- `active_issue_id`
- `active_attempt_id`
- `active_worktrees`
- `alert_counts`

Suggested `run_state` values:

- `initializing`
- `running`
- `stopping`
- `completed`
- `aborted`

### AlertEvent

This is the normalized event object for notifications.

Suggested fields:

- `alert_id`
- `run_id`
- `issue_id` optional
- `severity`
- `event_type`
- `summary`
- `details`
- `created_at`
- `delivery_status`

Suggested `severity` values:

- `info`
- `warning`
- `critical`

## State Domains

NightShift must keep these domains separate:

- `IssueState`
- `AttemptState`
- `DeliveryState`
- `blocker_type`
- `progress_type`

Do not collapse these into one string field.

## Minimal Persistence Rule

The MVP persistence layer should be able to reconstruct:

- current issue state
- current run state
- latest accepted branch for each issue
- full attempt history for a run
- alert history

That is the minimum needed for recovery, reporting, and morning review.
