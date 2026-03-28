# Delivery / PR Dispatcher MVP

## Purpose

This document defines the smallest product-layer delivery workflow needed to close the NightShift loop after an issue has already been accepted by the kernel.

It is intentionally narrow:

- no merge automation
- no review-thread sync
- no PR update policy beyond the first submission
- no provider abstraction beyond GitHub for the first version

The goal is only to make this path real:

`accepted issue -> push branch -> create PR -> record delivery linkage`

## Alignment With V4.2.1

This design stays within the existing V4.2.1 boundaries.

- The stable kernel remains unchanged.
- The kernel still decides execution, validation, acceptance, rejection, rollback, and persistence of run history.
- Delivery remains a product-layer edge module, matching the V4.2.1 `PR Dispatcher` concept.

This design does not move PR creation into the kernel.

Instead it operationalizes the product-layer handoff after acceptance:

`kernel accepted result -> product delivery action -> PR created -> delivery state recorded`

## Scope

The MVP covers:

- explicit delivery for accepted issues
- optional `--deliver` convenience on `run`
- git commit for accepted worktree changes
- git push to `origin`
- GitHub pull request creation
- `IssueRecord` delivery linkage updates

The MVP does not cover:

- auto merge
- reviewer assignment policy
- label automation
- PR comment synchronization
- update-existing-PR logic
- branch rebasing
- cross-provider support

## Delivery Trigger Model

The first version supports two entry points with one shared delivery action underneath.

### Primary Action

`nightshift deliver --issues <issue_id...>`

This is the authoritative delivery command.

It is explicit, auditable, and can be retried independently from execution.

### Convenience Action

`nightshift run --issues <issue_id...> --deliver`

This does not implement separate delivery logic.

It only means:

1. execute the selected issues
2. collect the accepted subset
3. invoke the same delivery action used by `nightshift deliver`

The same pattern can later extend to `run --all --deliver`.

## Admission Rules

An issue is deliverable only if all of the following are true:

- `IssueRecord.issue_state == done`
- `IssueRecord.attempt_state == accepted`
- `IssueRecord.branch_name` is present
- `IssueRecord.worktree_path` is present
- the worktree still exists
- the worktree has a non-empty diff relative to the target base branch, or a commit has not yet been created for delivery

Delivery must fail closed if any of these are not true.

Delivery must not try to reinterpret rejected, aborted, or incomplete execution outputs as ready for PR submission.

## Source Of Truth

Delivery reads from:

- immutable `IssueContract`
- current mutable `IssueRecord`
- the accepted worktree referenced by `IssueRecord.worktree_path`

Delivery writes back only through the `IssueRegistry` delivery linkage interface:

- `attach_delivery(issue_id, delivery_state, delivery_id=None, delivery_ref=None)`

Run-scoped attempt history remains owned by the `StateStore`.

## Git Behavior

For each accepted issue:

1. resolve the accepted worktree
2. verify the branch recorded in `IssueRecord.branch_name`
3. stage tracked and untracked changes needed for the accepted result
4. create a delivery commit
5. push the branch to `origin`
6. create a PR against the configured base branch

The first version assumes:

- one accepted issue maps to one branch
- one branch maps to one PR
- the remote is `origin`

## Commit Policy

The first version uses a deterministic commit message template:

`feat(issue): <issue_id> <short title>`

Example:

`docs(issue): GH-7 增加中文 README 说明`

The exact prefix may vary by issue kind later, but the MVP can start with a single stable template if needed.

## PR Policy

The first version uses a deterministic PR template with:

- title derived from issue id and title
- body including:
  - issue link or source reference when available
  - short acceptance summary
  - verification commands from contract
  - note that the change was delivered by NightShift

The MVP only creates a new PR.

If `IssueRecord.delivery_ref` is already present, delivery should fail with a clear message unless the operator explicitly asks for a new PR path in a later version.

## Delivery State Model

The first version uses these delivery states:

- `none`
- `submitted`
- `failed`

Semantics:

- `none`: no delivery has been attempted
- `submitted`: PR creation succeeded and linkage was recorded
- `failed`: delivery was attempted but did not complete

Failure to deliver must not rewrite acceptance state.

An accepted result remains accepted even if push or PR creation fails.

## Failure Handling

Typical failure points:

- no remote named `origin`
- git commit fails
- git push fails
- GitHub token missing
- PR creation fails
- issue already delivered

The MVP behavior should be:

- stop delivery for the affected issue
- record `delivery_state=failed`
- preserve accepted execution state
- emit operator-friendly output showing where to inspect the failure

For batch delivery, the first version may use fail-fast semantics to match the current run batch model.

## CLI Shape

Recommended first-version commands:

```bash
nightshift deliver --issues GH-7 --config /path/to/nightshift.yaml
nightshift run --issues GH-7 --config /path/to/nightshift.yaml --deliver
```

Optional later additions:

- `nightshift deliver --all-accepted`
- `nightshift deliver show GH-7`

These are not required for the MVP.

## Required Configuration

The MVP needs explicit delivery-side configuration in `nightshift.yaml`, such as:

- repository full name, for example `GM-HZ/nightshift`
- base branch, default `master`
- remote name, default `origin`
- token source policy, initially `GITHUB_TOKEN` or `NIGHTSHIFT_GITHUB_TOKEN`

This config belongs to product workflow, not kernel state.

## Data Flow

The intended product flow becomes:

`requirement -> split -> review -> publish issue -> ingest -> queue add -> run -> validate -> accepted -> deliver -> PR`

The delivery step starts only after the kernel has already produced an accepted outcome.

## Testing Strategy

The MVP should be verified at three levels.

### Unit Tests

- deliverability admission checks
- commit message / PR payload rendering
- duplicate-delivery refusal
- delivery state transitions

### Service Tests

- accepted issue with valid worktree creates commit/push/PR via seams
- push failure records `delivery_state=failed`
- PR creation failure records `delivery_state=failed`

### Workflow Rehearsal

Use the already-validated Chinese README flow and extend it one step further:

`requirement -> split -> publish -> ingest -> queue -> run -> deliver -> PR`

Success for the full rehearsal means:

- the issue remains `done + accepted`
- `delivery_state=submitted`
- `delivery_ref` points at the created PR

## Recommended Implementation Order

1. delivery config model
2. deliverability gate
3. git delivery service
4. GitHub PR create adapter
5. CLI `deliver`
6. `run --deliver` convenience hook
7. workflow rehearsal
