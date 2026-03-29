# NightShift

> Language / 语言：English | [简体中文](README.zh-CN.md)

NightShift is an overnight AI coding system for turning a requirement into a reviewable change, running it through an engine, and keeping a durable record of what happened. This repository is organized around the `v4.2.1` product direction.

## Current Status

- Active target: `v4.2.1`
- Kernel: implemented and verified
- Live operator surface: kernel-first plus queue admission, work-order materialization, and batch execution via `run --issues` / `run --all`
- Broader product workflow: still primarily a design direction above the current live surface
- Best current code-aligned summary: [current capability truth matrix](/Users/gongmeng/dev/code/nightshift/docs/architecture/coverage/current-capability-truth-matrix.md)

## What Works Today

- immutable contracts and mutable current issue records
- queue admission from approved execution work orders
- queue inspection and reprioritization
- product-facing batch execution via `run --issues` and `run --all`
- single-issue execution via `run-one`
- recovery and minimal historical reporting
- layered `.nightshift` migration for project config, contract storage, and runtime storage

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
- Current live capability baseline: [docs/architecture/coverage/current-capability-truth-matrix.md](/Users/gongmeng/dev/code/nightshift/docs/architecture/coverage/current-capability-truth-matrix.md)
- Product documentation design: [docs/architecture/product/documentation-information-architecture.md](/Users/gongmeng/dev/code/nightshift/docs/architecture/product/documentation-information-architecture.md)
- Product coverage: [docs/architecture/coverage/nightshift-v4.2.1-coverage-matrix.md](/Users/gongmeng/dev/code/nightshift/docs/architecture/coverage/nightshift-v4.2.1-coverage-matrix.md)
- Specs and design history: [docs/superpowers/specs/README.md](/Users/gongmeng/dev/code/nightshift/docs/superpowers/specs/README.md)
- Historical verification and rehearsal evidence: [docs/2026-03-28-workflow-verification-report.md](/Users/gongmeng/dev/code/nightshift/docs/2026-03-28-workflow-verification-report.md), [docs/rehearsals/2026-03-29-gh7-product-e2e/README.md](/Users/gongmeng/dev/code/nightshift/docs/rehearsals/2026-03-29-gh7-product-e2e/README.md)
- Contributor note: [docs/local-development.md](/Users/gongmeng/dev/code/nightshift/docs/local-development.md)
