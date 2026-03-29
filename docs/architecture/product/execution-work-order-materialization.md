# Execution Work Order Materialization

## Status

Working product design aligned to `v4.2.1`.

This document defines how NightShift should materialize an approved `Execution Work Order` into an immutable runtime `IssueContract`.

It builds on:

- `docs/architecture/product/execution-work-order-information-model.md`
- `docs/architecture/product/config-and-workspace-model.md`

## Why This Exists

NightShift now has a clearer planning-to-execution model:

`Requirement Issue -> Proposal -> Execution Branch + Execution Work Order -> Draft PR -> IssueContract -> Run`

What still needs a precise rule is the transition from:

- editable execution workbook

to:

- immutable runtime contract

Without that boundary, the system becomes ambiguous in exactly the place where unattended execution needs the strongest guarantees.

## Design Goal

NightShift should treat the `Execution Work Order` as the approved execution source and the `IssueContract` as the frozen runtime projection of that source.

The materialization process should:

- reject under-specified work orders
- allow project defaults to fill policy-oriented gaps
- preserve provenance
- give `run` a stable, non-ambiguous contract

## Core Principle

Execution-critical information must come explicitly from the `Execution Work Order.execution` block.

NightShift must not infer decisive runtime fields from:

- the `rationale` block
- Markdown body prose
- PR body text
- issue comments
- external links

Project defaults may fill policy-style fields, but not execution meaning.

## Materialization Boundary

### Editable Artifact

The `Execution Work Order` remains editable while it is under planning and review.

### Frozen Artifact

The `IssueContract` is immutable once materialized.

`run` consumes only the frozen contract.

`run` does not reinterpret or re-read the work order as part of normal execution.

## Freeze Point

The freeze point should be:

- `queue add`

This means:

1. operator reviews or updates the work order
2. operator runs `queue add`
3. NightShift validates and materializes the work order
4. NightShift writes the immutable contract
5. later `run` uses that contract only

This keeps the mental model simple:

- work order is still editable before queue admission
- queue admission is the explicit freeze action
- execution runs only on frozen inputs

## Field Model

`Execution Work Order` should support two categories of materialized fields:

1. fields that must be explicitly present in the work order
2. fields that may be filled from project defaults

## Required Work Order Fields

The following fields must be explicitly present in `execution`.

If any are missing, materialization must fail.

- `title`
- `goal`
- `allowed_paths`
- `non_goals`
- `acceptance_criteria`
- `context_files`

For verification, one of these must be present:

- `verification`
- `verification_commands`

## Defaultable Fields

The following fields may be filled from project defaults when absent from the work order:

- `priority`
- `forbidden_paths`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`
- `engine_hints`

These are policy and environment controls, not the core semantic meaning of the work.

## Verification Input Shapes

The work order should support two verification shapes.

### Shape A: Simple Verification Command List

```yaml
verification_commands:
  - test -s README.zh-CN.md
  - rg -n "README\\.zh-CN\\.md" README.md
```

### Shape B: Explicit Validation Structure

```yaml
verification:
  issue_validation:
    - test -s README.zh-CN.md
  regression_validation:
    - rg -n "README\\.zh-CN\\.md" README.md
  promotion_validation: []
```

## Verification Normalization Rule

If `verification` is present:

- NightShift uses it directly after schema validation

If only `verification_commands` is present:

- NightShift normalizes it into the structured validation shape

Recommended first-pass normalization:

- `issue_validation = verification_commands`
- `regression_validation = verification_commands`
- `promotion_validation = []`

## Verification Ambiguity Rule

If both `verification` and `verification_commands` are present:

- materialization must fail

This avoids silent precedence rules that would confuse operators.

## ID Model

The work order and the runtime issue must be related, but not permanently forced to be the same object.

### `work_order_id`

This is the stable identity of the execution workbook.

It is used for:

- work order file naming
- archive traceability
- branch and PR linkage
- long-lived historical reference

### `issue_id`

This is the NightShift runtime execution identity.

### Default Rule

If `execution.issue_id` is absent:

- `IssueContract.issue_id = work_order_id`

If `execution.issue_id` is present:

- use the explicit runtime issue id
- keep the link back to `work_order_id`

## Provenance Fields

Every materialized `IssueContract` should carry enough provenance to reconstruct where it came from.

Recommended provenance fields:

- `work_order_id`
- `work_order_path`
- `work_order_revision`
- `source_issue`
- `source_branch`
- `source_pr`

The exact runtime schema can evolve, but those concepts should be preserved.

## Revision Rule

The contract must preserve which version of the work order was frozen.

The first-pass recommended provenance key is:

- git commit SHA of the execution branch HEAD at materialization time
- plus the work order file path

This gives NightShift a stable way to answer:

- which work order produced this contract
- which revision of that work order was frozen

## Drift Rule

After materialization, the work order may still be edited in the branch or draft PR.

If the work order changes after freeze:

- the previously materialized contract is no longer the current one
- NightShift must require a new `queue add`
- the new `queue add` creates a new contract from the new work order revision

NightShift must not silently keep using an outdated contract while pretending it reflects the current work order.

## Contract History Rule

Rematerialization should not overwrite historical provenance.

The system should preserve:

- the previous materialized contract or contract revision
- the fact that a newer work order revision superseded it

The exact on-disk storage format can be decided later, but the history must remain auditable.

## Materialization Algorithm

Recommended first-pass flow:

1. locate the primary work order for the execution branch
2. parse frontmatter
3. validate the work order schema
4. verify required execution fields are present
5. reject if both verification shapes are present
6. normalize verification into structured validation form
7. fill defaultable fields from project config
8. capture provenance fields
9. write the immutable `IssueContract`
10. update queue-admitted mutable state to point at the frozen contract revision

## Materialization Failure Rule

If materialization fails:

- `queue add` fails
- no execution-ready contract is written
- the work order remains editable
- the issue does not enter the runnable queue

This preserves the current NightShift principle:

- no unattended execution without an executable, validated input surface

## Relationship To `v4.2.1`

This design stays aligned with `v4.2.1`:

- immutable runtime contract remains required
- admission still exists before unattended execution
- defaults are still allowed, but only from explicit policy sources
- execution and runtime history remain separate from planning and rationale

What this document changes is not the kernel principle.

It tightens the product-side handoff so the kernel receives a more trustworthy input.

## Relationship To Future `.nightshift/` Migration

This materialization model is compatible with the target layout:

- work orders under `.nightshift/work-orders/`
- contracts under `.nightshift/contracts/`

It does not require immediate storage migration to define the rule correctly.

## Deferred Questions

This document does not yet define:

- exact contract file naming under `.nightshift/contracts/`
- whether queue admission should keep multiple frozen revisions side by side
- how drift is surfaced in CLI output
- how delivery should reference the exact contract revision used for the accepted run

Those should be resolved in implementation planning.
