# Delivery Closure Model

## Status

Working product design aligned to `v4.2.1`.

This document defines how NightShift should close the loop from an accepted execution result to a governed reviewable PR without relying on the mutable current worktree.

## Problem

The repository now has a live path through:

`GitHub issue -> work order -> queue add -> run`

But the product loop still breaks after acceptance:

- there is no live `deliver` command
- accepted results are not frozen for delivery
- PR creation is not currently governed by NightShift

That leaves a gap between:

- what NightShift validated
- what eventually gets shipped for human review

If delivery reads the current worktree directly, post-acceptance drift can leak into the PR.

## Goal

NightShift should be able to take an accepted attempt and turn it into a reviewable PR through an explicit, auditable delivery step.

The delivery input must be the accepted result that NightShift validated, not whatever happens to be in the worktree later.

## Approaches Considered

### 1. Deliver From Current Worktree With Guardrails

Use the current worktree, re-check allowed paths, then commit and push.

Pros:

- smallest implementation
- reuses existing branch/worktree state

Cons:

- still depends on mutable post-acceptance state
- does not truly freeze the validated result
- makes auditability weaker

### 2. Freeze Accepted Result At Acceptance, Then Deliver Explicitly

When an attempt is accepted, NightShift writes a delivery snapshot artifact. Later `deliver` consumes that frozen artifact, reconstructs the branch state, and opens the PR.

Pros:

- ties delivery to the accepted result
- preserves a strong audit trail
- keeps delivery explicit and operator-friendly

Cons:

- more implementation than the current-worktree shortcut

### 3. Auto-Deliver Inside `run`

Make acceptance immediately push and open the PR.

Pros:

- shortest command chain

Cons:

- mixes execution and delivery concerns
- harder to retry or inspect delivery independently
- too big for the first recovery of live delivery

## Recommendation

Use **Approach 2**:

- freeze accepted result at acceptance time
- expose delivery as an explicit command
- let `deliver` consume the frozen snapshot, not the live worktree

This is the cleanest match for the current architecture:

- work order is the editable execution source
- `queue add` is the freeze point for contract
- accepted attempt becomes the freeze point for delivery input
- `deliver` is the explicit handoff into PR creation

## Core Model

The new path becomes:

`GitHub issue -> work order -> queue add -> IssueContract -> run -> accepted snapshot -> deliver -> PR`

### Freeze Points

NightShift now has two explicit freezes:

1. `queue add`
   - freezes approved work order into immutable `IssueContract`
2. accepted attempt
   - freezes the validated execution result into a delivery snapshot

These two freezes serve different purposes and should remain separate.

## Accepted Delivery Snapshot

When `run` ends in `attempt_state=accepted`, NightShift should write a delivery snapshot artifact under the accepted attempt artifact directory.

Recommended location:

`.nightshift/artifacts/runs/<run_id>/attempts/<attempt_id>/delivery/`

Recommended files:

- `snapshot.json`
- `changes.patch`

### `snapshot.json`

This should capture:

- `issue_id`
- `run_id`
- `attempt_id`
- `work_order_id`
- `work_order_revision`
- `contract_revision`
- `branch_name`
- `worktree_path`
- `pre_edit_commit_sha`
- `changed_paths`
- file digests for the changed paths
- source issue and source branch references

### `changes.patch`

This should be the frozen patch for the accepted result relative to the pre-edit commit.

The patch becomes the authoritative delivery payload.

## Delivery State Semantics

The current domain model already has:

- `none`
- `branch_ready`
- `pr_opened`
- `reviewed`
- `merged`
- `closed_without_merge`

Recommended semantics:

- after acceptance and snapshot freeze:
  - move `delivery_state` to `branch_ready`
- after PR creation:
  - move `delivery_state` to `pr_opened`

If delivery fails after a valid snapshot already exists, keep `delivery_state=branch_ready` and record the failure in delivery artifacts/events. In this model, `branch_ready` truly means “there is a frozen accepted result ready for governed delivery.”

## CLI Surface

First live recovery should be conservative:

- `nightshift deliver --issues <id1,id2,...>`

Out of scope for the first slice:

- `run --deliver`
- `deliver --all`
- auto-merge
- review-thread sync
- PR reopen/update policy

## Deliverability Gate

`deliver` should only accept issues that satisfy all of these:

- `issue_state=done`
- `attempt_state=accepted`
- `accepted_attempt_id` is set
- `delivery_state in {none, branch_ready}`
- accepted delivery snapshot exists

If any of those fail, `deliver` must stop with a short operator-friendly error.

## Delivery Execution Model

`deliver` should:

1. load current issue record and accepted attempt record
2. load the frozen delivery snapshot
3. reconstruct the accepted result on the issue branch from the snapshot
4. create a delivery commit if needed
5. push the branch
6. create a PR
7. write delivery linkage back to the issue record

The key rule is:

NightShift delivers the frozen accepted result, not the current worktree.

## Delivery Linkage

After successful PR creation, NightShift should attach:

- `delivery_state=pr_opened`
- `delivery_id=<pr_number>`
- `delivery_ref=<pr_url>`

The PR body should reference:

- source issue
- work order id
- accepted run id
- accepted attempt id

## Relationship To Current Architecture

This does not change the kernel boundary.

Kernel still governs:

- execution
- validation
- recovery
- runtime persistence

Delivery remains a product-side orchestration layer above the kernel.

## Success Criteria

This design is successful when:

- accepted execution results are frozen before delivery
- `deliver` can open a PR from that frozen result
- delivery linkage on `IssueRecord` remains authoritative
- NightShift can close the loop without relying on mutable current worktree state
