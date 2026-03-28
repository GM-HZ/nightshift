# NightShift Product Workflow

This section describes the parts of NightShift that sit above the kernel and are not yet complete in the current repository.

It should be read as the current product-layer planning boundary, not as a final code-layout commitment.

## Product Workflow Status

The broader product workflow is not yet fully implemented.

The kernel can already execute approved work once an execution-ready issue exists.

What is still missing is the workflow around getting work into the kernel and delivering the result back out.

This is the area where the architecture is still expected to evolve the most.

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

## Important Boundary

Today the repository supports:

- execution-ready issue in
- kernel execution
- run history out

It does not yet support the full product chain:

- external request in
- automated proposal and approval
- automated delivery and PR creation

## Design Sources

The main design references for the product workflow side are:

- `docs/superpowers/specs/nightshift-v4.2.1/05-requirement-splitter-and-context-loading.md`
- `docs/superpowers/specs/nightshift-v4.2.1/06-cli-config-persistence-alerting.md`
- `docs/superpowers/specs/nightshift-v4.2.1/07-language-and-phasing.md`

Current product-slice design docs:

- `docs/architecture/product/issue-ingestion-mvp.md`
- `docs/architecture/product/execution-selection-mvp.md`
- `docs/architecture/product/queue-admission-mvp.md`

Current product-slice implementation status:

- `issue ingest-github` now exists as the first product-layer bridge into the kernel
- it currently supports one GitHub issue at a time
- it enforces provenance and admission before writing `IssueContract` and `IssueRecord`
- `issue ingest-github --materialize-only` now supports review-first materialization
- `queue add` now explicitly admits local issues into the live queue
- `run --issues` and `run --all` now exist for sequential fail-fast batch execution
- batch execution currently reuses kernel `run-one` and current queue ordering
- richer intake flow such as splitter-driven issue creation and proposal review UX still remain future work

## Current Next-Step Theme

The next meaningful step above the kernel is expanding the current intake-plus-selection path so it can turn external requests into:

- immutable `IssueContract`
- current `IssueRecord`

without requiring manual hand-authoring of both files every time.
