# NightShift Product Workflow

This section is the product-design entry point above the kernel.
It describes the product-side models and boundaries, not the operator guide.

If you want to use NightShift, start with [../../usage/README.md](../../usage/README.md).

## Product Workflow Status

The broader product chain is usable today in MVP form.

The kernel can execute approved work once an execution-ready issue exists, and the surrounding flow now covers issue intake, queue admission, execution selection, and delivery with simplifications that are called out in the coverage matrix.

The remaining design work is about tightening the product-side models and reducing the manual seams around that chain.

## What Belongs To Product Workflow

These areas are outside the stable kernel boundary in `v4.2.1`:

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
- `docs/architecture/product/contract-context-field-expansion.md`
- `docs/architecture/product/documentation-information-architecture.md`
- `docs/architecture/product/execution-work-order-information-model.md`
- `docs/architecture/product/execution-work-order-materialization.md`
- `docs/architecture/product/splitter-proposal-review-mvp.md`
- `docs/architecture/product/issue-ingestion-mvp.md`
- `docs/architecture/product/queue-admission-mvp.md`
- `docs/architecture/product/execution-selection-mvp.md`
- `docs/architecture/product/delivery-pr-dispatcher-mvp.md`

## Important Boundary

Today the repository supports a usable chain from requirement and issue intake through kernel execution and delivery, but several steps are still MVP-shaped:

- splitter and proposal review are intentionally thin
- issue ingestion and queue admission are simpler than the target product model
- delivery works, but it is not a full release-management system

## Design Sources

The main design references for the product workflow side are:

- `docs/superpowers/specs/nightshift-v4.2.1/05-requirement-splitter-and-context-loading.md`
- `docs/superpowers/specs/nightshift-v4.2.1/06-cli-config-persistence-alerting.md`
- `docs/superpowers/specs/nightshift-v4.2.1/07-language-and-phasing.md`

## Current Next-Step Theme

The current design focus is the cross-cutting cleanup above the now-usable product chain:

- execution work order and issue-contract information model
- config and workspace model
- product-facing documentation and onboarding

These are the main seams still being tightened so the workflow feels more like a stable product and less like a stitched-together MVP.
