# NightShift

NightShift is an overnight AI coding system for turning a requirement into a reviewable change, running it through an engine, and keeping a durable record of what happened. This repository is organized around the `v4.2.1` product direction.

## Current Status

- Active target: `v4.2.1`
- Kernel: implemented and verified
- Product workflow: usable today, with some MVP-shaped simplifications still visible in the docs and operator flow
- Best current proof: [workflow verification report](/Users/gongmeng/dev/code/nightshift/docs/2026-03-28-workflow-verification-report.md) and [rehearsal archive](/Users/gongmeng/dev/code/nightshift/docs/rehearsals/2026-03-29-gh7-product-e2e/README.md)

## What Works Today

- requirement splitting and proposal review
- GitHub issue ingestion into execution-ready contracts and records
- queue admission and queue inspection
- single-issue execution, recovery, and reporting
- delivery flow through to pull request creation in the current product chain

## Quickstart Path

If you are new to NightShift, read in this order:

1. [Usage entry](/Users/gongmeng/dev/code/nightshift/docs/usage/README.md)
2. [Install](/Users/gongmeng/dev/code/nightshift/docs/usage/install.md)
3. [Workflow](/Users/gongmeng/dev/code/nightshift/docs/usage/workflow.md)
4. [Configuration](/Users/gongmeng/dev/code/nightshift/docs/usage/configuration.md)
5. [Architecture entry](/Users/gongmeng/dev/code/nightshift/docs/architecture/README.md)

If you want the active spec set, continue to [docs/superpowers/specs/README.md](/Users/gongmeng/dev/code/nightshift/docs/superpowers/specs/README.md).

## Docs Map

- Usage: [docs/usage/README.md](/Users/gongmeng/dev/code/nightshift/docs/usage/README.md), [docs/usage/install.md](/Users/gongmeng/dev/code/nightshift/docs/usage/install.md), [docs/usage/configuration.md](/Users/gongmeng/dev/code/nightshift/docs/usage/configuration.md), [docs/usage/workflow.md](/Users/gongmeng/dev/code/nightshift/docs/usage/workflow.md), [docs/usage/deployment.md](/Users/gongmeng/dev/code/nightshift/docs/usage/deployment.md)
- Product and architecture: [docs/architecture/README.md](/Users/gongmeng/dev/code/nightshift/docs/architecture/README.md), [docs/architecture/product/README.md](/Users/gongmeng/dev/code/nightshift/docs/architecture/product/README.md)
- Product documentation design: [docs/architecture/product/documentation-information-architecture.md](/Users/gongmeng/dev/code/nightshift/docs/architecture/product/documentation-information-architecture.md)
- Product coverage: [docs/architecture/coverage/nightshift-v4.2.1-coverage-matrix.md](/Users/gongmeng/dev/code/nightshift/docs/architecture/coverage/nightshift-v4.2.1-coverage-matrix.md)
- Specs and design history: [docs/superpowers/specs/README.md](/Users/gongmeng/dev/code/nightshift/docs/superpowers/specs/README.md)
- Verification and rehearsal evidence: [docs/2026-03-28-workflow-verification-report.md](/Users/gongmeng/dev/code/nightshift/docs/2026-03-28-workflow-verification-report.md), [docs/rehearsals/2026-03-29-gh7-product-e2e/README.md](/Users/gongmeng/dev/code/nightshift/docs/rehearsals/2026-03-29-gh7-product-e2e/README.md)
- Contributor note: [docs/local-development.md](/Users/gongmeng/dev/code/nightshift/docs/local-development.md)
