# NightShift Product Workflow

This section is the product-design entry point above the kernel.
It describes the product-side models and boundaries, not the operator guide.

If you want to use NightShift, start with [../../usage/README.md](../../usage/README.md).

## Product Workflow Status

The broader product workflow remains the active design direction above the kernel.

The live repository currently exposes queue admission and execution-work-order materialization above the kernel, but it does not currently expose the full product CLI surface described in older MVP documents.

Use the [current capability truth matrix](../coverage/current-capability-truth-matrix.md) when you need to know what is live in code today.

## What Belongs To Product Workflow

These areas remain outside the stable kernel boundary in `v4.2.1`:

- requirement splitter
- proposal review and approval flow
- issue ingestion into execution-ready contracts
- queue admission commands such as `queue add`
- multi-issue overnight control loop
- notifications
- richer reporting
- PR dispatcher and delivery automation

These items are grouped here as the current product-work boundary for planning purposes.

That grouping may still be refined as implementation work exposes better seams.

## Current Product Design Docs

The current product-side design work is centered on these documents:

- `docs/architecture/product/config-and-workspace-model.md`
- `docs/architecture/product/config-and-workspace-migration-plan.md`
- `docs/architecture/product/contract-storage-migration.md`
- `docs/architecture/product/runtime-state-migration.md`
- `docs/architecture/product/contract-context-field-expansion.md`
- `docs/architecture/product/documentation-information-architecture.md`
- `docs/architecture/product/delivery-closure-model.md`
- `docs/architecture/product/execution-work-order-information-model.md`
- `docs/architecture/product/execution-work-order-materialization.md`
- `docs/architecture/product/overnight-control-loop-mvp.md`
- `docs/architecture/product/user-space-operator-environment.md`

## Important Boundary

Today the repository has:

- a strong implemented kernel
- live queue admission plus execution work order materialization
- broader product workflow design work that is not fully represented in live code

That distinction matters more than the older MVP narrative.

## Design Sources

The main design references for the product workflow side are:

- `docs/superpowers/specs/nightshift-v4.2.1/05-requirement-splitter-and-context-loading.md`
- `docs/superpowers/specs/nightshift-v4.2.1/06-cli-config-persistence-alerting.md`
- `docs/superpowers/specs/nightshift-v4.2.1/07-language-and-phasing.md`

## Current Next-Step Theme

The current design focus is turning the now-usable product chain into a fuller governed loop:

- delivery closure from accepted result to PR
- execution work order and issue-contract information model
- config and workspace model

These are the main seams still being tightened so the workflow feels more like a stable product and less like a stitched-together MVP.
