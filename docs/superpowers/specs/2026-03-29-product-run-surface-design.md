# Product Run Surface Design

## Goal

Reintroduce a minimal product-facing execution surface without bringing back the older, larger product workflow all at once.

This design only restores:

- `nightshift run --issues <id1,id2,...>`
- `nightshift run --all`

It does **not** restore splitter, proposal review, GitHub issue ingestion, or delivery.

## Why This Slice

The current repository already has:

- a strong kernel
- queue admission
- frozen contract materialization from approved execution work orders

What is missing is a product-facing execution entrypoint above `run-one`.

This design fills that gap without reopening the full historical product CLI surface.

## Scope

In scope:

- `run --issues`
- `run --all`
- sequential execution
- fail-fast behavior
- short batch summary output
- reuse of current queue admission and kernel execution semantics

Out of scope:

- `split`
- `proposals`
- `issue ingest-github`
- `deliver`
- `run --deliver`
- continue-on-failure
- daemon mode
- stop / pause / resume
- dependency-aware scheduling

## Core Rule

`run --issues` and `run --all` only consume issues that have already been admitted through `queue add`.

That means:

- the execution work order has already been frozen into an immutable `IssueContract`
- `run` does not reinterpret work orders
- `run` does not perform new admission
- `run` does not create new contract revisions

## Commands

### `nightshift run --issues <id1,id2,...>`

Behavior:

- accept a comma-separated issue id list
- resolve each issue through the existing registry
- execute them in the given order
- stop immediately on first rejected or failed result
- print a short summary at the end

Expected use:

- explicit operator-selected execution
- small controlled batches

### `nightshift run --all`

Behavior:

- fetch the current schedulable issue list from `IssueRegistry.list_schedulable_records()`
- preserve the existing queue ordering semantics
- execute issues sequentially
- stop immediately on first rejected or failed result
- print a short summary at the end

Expected use:

- simple batch execution over the current queue

## Execution Semantics

The product run surface is only a thin layer above the kernel.

Internally it should:

- select issue ids
- call the existing `RunOrchestrator.run_one()` for each selected issue
- aggregate the per-issue results into a small batch summary

It should not:

- introduce a new kernel state machine
- duplicate `run-one` logic
- bypass queue admission

## Failure Model

First version behavior is fixed:

- sequential execution
- `fail_fast = true`

If any selected issue is:

- rejected by validation
- aborted by engine or recovery boundary
- otherwise fails to produce an accepted result

the batch stops immediately.

This keeps the first product run surface simple and predictable.

## Output

First version output should stay short.

Per successful issue:

- reuse the existing `run-one` style summary shape where practical

Batch summary:

- number requested
- number completed
- whether the batch stopped early
- last run id or failing issue id when relevant

No new report format is required in this slice.

## Relationship To Existing Commands

- `run-one` remains the lowest-level explicit execution command
- `run --issues` and `run --all` become the product-facing execution surface
- `recover` and `report` remain unchanged

Resulting operator path:

`approved work order -> queue add -> run --issues|run --all -> recover/report`

## Design Constraints

This slice must preserve these current truths:

- `queue add` is the freeze point
- `IssueContract` remains immutable during execution
- current mutable state stays in `IssueRecord`
- kernel remains the execution authority

## Testing Expectations

The implementation should cover:

- explicit issue list selection
- `run --all` selection from schedulable queue
- fail-fast stop behavior
- stable ordering
- CLI summary output
- reuse of existing kernel behavior instead of reimplementing execution logic

## Recommended Implementation Shape

1. add a small product-side batch runner module
2. add `run --issues` and `run --all` CLI commands
3. add a lightweight batch result model
4. sync usage docs to point operators at the new product-facing run surface

## Success Criteria

This slice is successful when:

- the repository once again has a live product-facing run surface
- that surface is clearly narrower than the full historical product chain
- documentation can honestly say that batch execution is live
- no old splitter / ingestion / delivery claims need to come back with it
