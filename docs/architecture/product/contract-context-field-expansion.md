# Contract Context Field Expansion

## Status

Working product design aligned to `v4.2.1`.

This document describes a small, deliberate expansion of `IssueContract` so it can carry a more complete frozen execution context.

## Purpose

NightShift currently freezes the most essential execution data into `IssueContract`, but two pieces of already-reviewed execution context still live only in the `Execution Work Order`:

- `non_goals`
- `context_files`

Those fields are useful after freeze for:

- operator inspection
- audit and review
- later agent/context-loader evolution

The purpose of this change is to make the frozen contract a more faithful snapshot of the approved execution input.

This is not intended to change runtime orchestration behavior in the first pass.

## Alignment With `v4.2.1`

This change is consistent with `v4.2.1` because it preserves the same core principles:

- unattended execution still depends on a frozen immutable contract
- planning artifacts remain separate from runtime artifacts
- NightShift still materializes before execution rather than guessing during execution
- runtime history remains separate from planning rationale

This is a contract-completeness refinement, not a kernel-boundary change.

## Why Make This Change

### Current Gap

Today, `non_goals` and `context_files` are validated during Work Order handling but are not first-class fields in the resulting runtime contract.

That means the frozen runtime artifact does not yet fully preserve:

- what the execution explicitly should not do
- which repository files were considered required execution context

### Desired Outcome

After this change, the immutable contract should preserve those two fields directly.

That gives NightShift a better long-term handoff surface without forcing immediate behavioral changes.

## Scope Of The First Pass

The first pass should do only these things:

- add `non_goals` to `IssueContract`
- add `context_files` to `IssueContract`
- materialize them from the approved `Execution Work Order`
- persist them anywhere the contract is persisted today
- expose them lightly in `queue show`

The first pass should not:

- change run orchestration logic
- change validation behavior
- change queue policy
- make context loading mandatory from contract fields

## Intended Roles

### `non_goals`

`non_goals` should represent the explicitly frozen negative scope of the execution slice.

In the first pass, it should be used for:

- traceability
- operator inspection
- post-run review context

### `context_files`

`context_files` should represent the explicitly frozen set of files the execution slice depends on as must-read context.

In the first pass, it should be used for:

- traceability
- operator inspection
- stable input for future context-loading improvements

## Why Not Leave Them Only In The Work Order

Keeping them only in the Work Order would leave the runtime contract incomplete.

That creates an avoidable gap between:

- the approved execution workbook
- the frozen runtime artifact

NightShift should not require later readers to reopen a historical Work Order just to understand core execution boundaries that were already known at freeze time.

## Why Not Make Them Runtime Constraints Immediately

That would be a larger change than this one needs to be.

If `non_goals` and `context_files` immediately become runtime-driving policy inputs, this small contract change would spill into:

- orchestrator behavior
- validation semantics
- queue policy
- context-loading guarantees

That would turn a clean information-model improvement into a multi-layer runtime behavior change.

The safer path is:

1. make them first-class frozen contract fields
2. let future work decide how runtime systems consume them

## Alternatives Considered

### Option A: Keep Current Behavior

Do not add the fields to `IssueContract`.

Rejected because it leaves the runtime artifact less complete than the approved execution source.

### Option B: Add The Fields And Also Enforce Runtime Policy

Add them to `IssueContract` and immediately make runtime systems depend on them.

Rejected for now because it is a larger cross-cutting behavior change than needed.

### Option C: Add A Separate Execution Metadata Object

Keep `IssueContract` unchanged and store `non_goals` / `context_files` in another runtime-adjacent object.

Rejected because it creates another layer of indirection and weakens the role of `IssueContract` as the main frozen runtime input.

## Chosen Approach

Expand `IssueContract` itself.

That means:

- `non_goals` becomes a first-class contract field
- `context_files` becomes a first-class contract field
- both are filled during Work Order materialization
- both are preserved across contract persistence and revision history

## CLI Visibility

The first operator-facing visibility change should be in `queue show`.

Recommended display:

- `non_goals_count=<n>`
- `context_files=<comma-separated list>`

This keeps the command useful without turning it into a full Work Order dump.

## Materialization Rule

Both fields should continue to come from the approved `Execution Work Order.execution` block.

They should not be defaulted from project config.

If they are missing there, materialization behavior should remain exactly what the Work Order schema already requires.

## Relationship To Future Work

This expansion intentionally prepares for later improvements such as:

- stronger context loading from contract data
- richer run/report inspection
- agent prompt construction from frozen context
- stricter scope review and post-run analysis

Those later improvements should build on these fields rather than reintroduce another metadata layer.

## Summary

This change is worth doing because it:

- keeps `IssueContract` more faithful to the approved execution input
- fits the `v4.2.1` model
- keeps scope small
- avoids mixing an information-model cleanup with runtime-policy redesign
