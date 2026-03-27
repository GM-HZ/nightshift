# NightShift V4.2 Detailed Design Pack

Status: legacy base pack retained because V4.2.1 still references it where historical inheritance is needed.

Implementation rule:

- do not use this pack as the default implementation target
- prefer `../README.md` and `../2026-03-27-nightshift-v4.2.1-unified-spec.md`
- only read this pack when a V4.2.1 document explicitly points back to it

This directory contains the detailed design documents that sit under the unified architecture spec:

- Parent architecture spec:
  [../2026-03-27-nightshift-v4.2-unified-spec.md](../2026-03-27-nightshift-v4.2-unified-spec.md)
- Chinese parent architecture spec:
  [../2026-03-27-nightshift-v4.2-unified-spec.zh-CN.md](../2026-03-27-nightshift-v4.2-unified-spec.zh-CN.md)

## Reading Order

1. `01-domain-model.md`
2. `02-kernel-interfaces.md`
3. `03-state-machines.md`
4. `04-engine-adapters-and-workspaces.md`
5. `05-requirement-splitter-and-context-loading.md`
6. `06-cli-config-persistence-alerting.md`
7. `07-language-and-phasing.md`

## Why A Separate Folder

V4.2 is the unified architecture. It defines:

- product boundary
- kernel boundary
- stable module seams
- high-level runtime rules

The files in this folder define the next layer down:

- data structures
- interface contracts
- state transitions
- engine integration rules
- persistence rules
- operational concerns

Keeping these documents in a separate folder prevents the unified spec from turning into an unreadable implementation dump.

## Cross-Cutting Rules

All detailed designs in this folder assume:

- NightShift is the harness and source of truth
- Codex CLI and Claude Code CLI are execution engines
- humans approve automation entry and merge
- execution issues must have executable validation
- branch and worktree isolation are mandatory
- issue state, attempt state, and delivery state are separate domains

## Current Language Direction

The current recommendation is:

- Python for the kernel and CLI harness
- TypeScript later if a dashboard or web control plane is needed

That recommendation is explained in `07-language-and-phasing.md`.
