# 04. Engine Adapters And Workspaces

## Purpose

V4.2.1 inherits the V4.2 adapter and workspace model and clarifies the separation between authoritative attempt records and bulky attempt artifacts.

Base source:

- [../nightshift-v4.2/04-engine-adapters-and-workspaces.md](../nightshift-v4.2/04-engine-adapters-and-workspaces.md)

Where this document adds rules, it supersedes the V4.2 text.

## Base Rules

The following V4.2 rules remain unchanged:

- adapters declare capabilities
- engine outcomes are normalized
- execution is worktree-local
- rollback is harness-controlled
- fallback is policy-controlled

## Attempt Record vs Artifact Directory

V4.2.1 separates:

- authoritative attempt metadata
- attempt-local execution artifacts

Authoritative attempt metadata lives in:

```text
nightshift-data/runs/<run_id>/attempts/<attempt_id>.json
```

Attempt artifacts live in a separate artifact directory such as:

```text
nightshift-data/runs/<run_id>/artifacts/attempts/<attempt_id>/
```

This separation is intentional:

- JSON records stay small and easy to load
- stdout, stderr, prompts, and validation outputs can grow without distorting record layout
- reporting tools can enumerate attempt records without scanning large artifact trees

## Artifact Directory Rule

Each `AttemptRecord` should carry an `artifact_dir` pointer to the attempt artifact directory.

Artifacts should include:

- rendered prompt or context bundle
- stdout
- stderr
- normalized outcome JSON
- validation result JSON
- optional engine-native structured artifacts

## Invocation Protocol

The recommended V4.2.1 flow is:

1. Build a context bundle.
2. Create the authoritative attempt record path.
3. Create the per-attempt artifact directory.
4. Start the engine in the isolated worktree.
5. Enforce timeout from the harness side.
6. Capture stdout and stderr into the artifact directory.
7. Capture any engine-produced structured artifacts into the artifact directory.
8. Normalize the result into `EngineOutcome`.
9. Save the finalized `AttemptRecord`.

## Recovery Consequence

Recovery should decide whether an interrupted attempt can move from `executing` to `validating` by inspecting the authoritative `AttemptRecord` plus the artifact directory.

It should not infer attempt completeness from file presence alone without a persisted record update.

## Recommended Layout

Recommended worktree layout:

```text
.nightshift/worktrees/issue-<issue_id>/
```

Recommended run layout:

```text
nightshift-data/runs/<run_id>/
  run-state.json
  events.ndjson
  issues/
    <issue_id>.json
  attempts/
    <attempt_id>.json
  artifacts/
    attempts/
      <attempt_id>/
```
