# Configuration

NightShift currently has two config stories:

- the implemented MVP compatibility layout
- the target layered model described in the architecture docs

## Current MVP Compatibility

Today, the repository still centers on a root `nightshift.yaml` and the existing repo-local data layout.

Typical current paths are:

- `nightshift.yaml`
- `nightshift/issues/`
- `nightshift-data/issue-records/`
- `nightshift-data/runs/`
- `nightshift-data/active-run.json`

The current config file controls:

- repository location and default branch
- default engine choice
- validation commands
- issue defaults
- retry policy
- worktree and artifact roots
- report output location

A minimal example lives in [../../examples/nightshift.yaml](../../examples/nightshift.yaml).

In the current implementation, `queue add` is also the freeze point for Work Orders:

- NightShift reads the current approved Work Order
- materializes an immutable `IssueContract`
- writes the current frozen contract under `nightshift/issues/`
- preserves revision history under `nightshift/contracts/<issue_id>/`
- freezes approved execution context such as `non_goals` and `context_files`

If the Work Order changes later, a new `queue add` is required so NightShift can freeze a new contract revision.

## Target Direction

The long-term model is split into:

- user space: `~/.nightshift/`
- project space: `<repo>/.nightshift/`

That target model is still a design direction in the docs. Do not treat it as the current on-disk layout unless the specific repository has already migrated.

## What Is Versioned

In the target model, versioned project material should include:

- project config
- work orders
- immutable contracts
- archived execution records

## What Is Runtime-Only

In the target model, runtime-only material should include:

- run history
- attempt artifacts
- transient reports
- local logs and caches

## Practical Rule

If you are setting up the current MVP today, use `nightshift.yaml` plus the existing repo-local directories.
If you are designing the next layout, use the layered `~/.nightshift/` and `.nightshift/` model as the reference boundary.
