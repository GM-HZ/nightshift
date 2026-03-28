# NightShift Kernel

This section describes the NightShift kernel as it is defined in `v4.2.1` and as it exists in the current repository.

It is intentionally a boundary description, not a claim that the current source tree is already physically organized as a dedicated `kernel/` package.

## Kernel Status

The kernel is treated as implemented and verified.

That statement means:

- the stable kernel modules from `v4.2.1` exist in code
- the supporting persistence and workspace layers required by the kernel also exist
- the kernel has passed both automated verification and real operator-style rehearsal within its current scope

This status is about capability and verification, not about final directory structure.

## What Counts As The Kernel

Per `v4.2.1`, the stable kernel consists of:

- Issue Registry
- Run Orchestrator
- Engine Adapter Layer
- Validation Gate

Supporting infrastructure that is required for the kernel to function:

- Workspace Manager
- State Store

This should be read as the current architectural ownership boundary for the repository.

It should not yet be read as a promise that every current module placement is final.

## What The Kernel Can Do Today

- load immutable issue contracts and current issue records
- inspect the current queue
- execute one issue with `run-one`
- validate and accept or reject an attempt
- persist run state, attempt history, issue snapshots, events, and alerts
- recover interrupted runs
- generate a minimal historical run report

## Verification Basis

The kernel has been validated through:

- automated test coverage in `tests/`
- full suite verification
- operator-style workflow rehearsal captured in:
  - `docs/2026-03-28-workflow-verification-report.md`

## Key Source Documents

- `docs/superpowers/specs/2026-03-27-nightshift-v4.2.1-unified-spec.md`
- `docs/superpowers/specs/nightshift-v4.2.1/01-domain-model.md`
- `docs/superpowers/specs/nightshift-v4.2.1/02-kernel-interfaces.md`
- `docs/superpowers/specs/nightshift-v4.2.1/03-state-machines.md`
- `docs/superpowers/specs/nightshift-v4.2.1/04-engine-adapters-and-workspaces.md`
- `docs/superpowers/specs/nightshift-v4.2.1/06-cli-config-persistence-alerting.md`
- `docs/superpowers/specs/nightshift-v4.2.1/07-language-and-phasing.md`

## Code Entry Points

- `src/nightshift/registry/`
- `src/nightshift/orchestrator/`
- `src/nightshift/engines/`
- `src/nightshift/validation/`
- `src/nightshift/workspace/`
- `src/nightshift/store/`
