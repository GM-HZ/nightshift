# 04. Engine Adapters And Workspaces

## Purpose

This document defines how NightShift interacts with external coding engines and how it isolates their execution environments.

## Engine Adapter Responsibilities

Each adapter must:

- declare capabilities
- verify the engine binary is available
- prepare invocation artifacts
- run the engine in a noninteractive overnight-safe mode
- capture stdout, stderr, and other artifacts
- normalize the final outcome

## Capability Contract

Each adapter must publish `EngineCapabilities`.

Minimum fields:

- `supports_streaming_output`
- `supports_structured_result`
- `supports_patch_artifact`
- `supports_resume`
- `supports_noninteractive_mode`
- `supports_worktree_execution`
- `supports_file_scope_constraints`
- `supports_timeout_enforcement`
- `supports_json_output_hint`

This lets the orchestrator answer:

- can this engine be used for this issue?
- should it be the primary or fallback engine?
- can this issue rely on structured result parsing?

## Outcome Contract

Each invocation must end as a normalized `EngineOutcome`.

Supported outcomes:

- `success`
- `engine_timeout`
- `engine_crash`
- `partial_output`
- `invalid_output`
- `interrupted`
- `environment_error`

Partial output must be preserved as artifacts even when the outcome is not `success`.

## Invocation Protocol

The recommended flow is:

1. Build a context bundle.
2. Materialize invocation files in a per-attempt artifact directory.
3. Start the engine in the isolated worktree.
4. Enforce timeout from the harness side.
5. Capture stdout and stderr.
6. Capture any engine-produced structured artifacts.
7. Normalize the result into `EngineOutcome`.

## Worktree Strategy

Each execution issue gets:

- one branch
- one isolated worktree

Recommended worktree layout:

- `.nightshift/worktrees/issue-<id>/`

Recommended artifact layout:

- `nightshift-data/runs/<run-id>/issues/<issue-id>/attempts/<attempt-id>/`

Artifacts should include:

- rendered prompt or context bundle
- stdout
- stderr
- normalized outcome JSON
- validation result JSON

## Workspace Lifecycle

The Workspace Manager should:

1. create or resume the issue worktree
2. ensure the expected branch is checked out
3. verify cleanliness before the attempt
4. record `pre_edit_commit_sha`
5. allow execution
6. rollback or retain based on orchestrator decision

## Rollback Rule

Rollback must be harness-controlled and worktree-local.

Rollback steps:

1. restore tracked files to `pre_edit_commit_sha`
2. remove non-whitelisted generated files
3. preserve only approved artifacts outside the worktree

The engine must not be trusted to clean up the workspace itself.

## Fallback Rule

The orchestrator may switch from one engine to another only when:

- the issue contract allows fallback
- the alternate adapter capabilities are sufficient
- the retry budget allows another attempt

Fallback should be recorded explicitly in:

- `AttemptRecord`
- event history
- reports

## Noninteractive Requirement

Overnight execution must prefer engines that support:

- noninteractive execution
- predictable artifact capture
- worktree-local execution

If an engine cannot run safely in this mode, it should not be eligible for unattended execution.
