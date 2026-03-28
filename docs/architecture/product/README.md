# NightShift Product Workflow

This section describes the parts of NightShift that sit above the kernel and are not yet complete in the current repository.

## Product Workflow Status

The broader product workflow is not yet fully implemented.

The kernel can already execute approved work once an execution-ready issue exists.

What is still missing is the workflow around getting work into the kernel and delivering the result back out.

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

## Current Next-Step Theme

The next meaningful step above the kernel is a minimal issue-ingestion path that can turn an external request into:

- immutable `IssueContract`
- current `IssueRecord`

without requiring manual hand-authoring of both files every time.
