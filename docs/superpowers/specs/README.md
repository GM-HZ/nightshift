# NightShift Specs Index

This index exists to keep implementation work anchored to one active design target and to prevent older design iterations from polluting the default reading path.

## Current Implementation Target

The current implementation target is:

- [2026-03-27-nightshift-v4.2.1-unified-spec.md](./2026-03-27-nightshift-v4.2.1-unified-spec.md)
- [nightshift-v4.2.1/README.md](./nightshift-v4.2.1/README.md)

If you are implementing NightShift now, start there.

## Minimal Reading Path

Use this path by default:

1. `2026-03-27-nightshift-v4.2.1-unified-spec.md`
2. `nightshift-v4.2.1/README.md`
3. `nightshift-v4.2.1/01-domain-model.md`
4. `nightshift-v4.2.1/02-kernel-interfaces.md`
5. `nightshift-v4.2.1/03-state-machines.md`
6. `nightshift-v4.2.1/04-engine-adapters-and-workspaces.md`
7. `nightshift-v4.2.1/05-requirement-splitter-and-context-loading.md`
8. `nightshift-v4.2.1/06-cli-config-persistence-alerting.md`
9. `nightshift-v4.2.1/07-language-and-phasing.md`

## Reference But Not Default

These documents remain in place because V4.2.1 still references them as historical or inheritance context:

- [2026-03-27-nightshift-v4.2-unified-spec.md](./2026-03-27-nightshift-v4.2-unified-spec.md)
- [nightshift-v4.2/README.md](./nightshift-v4.2/README.md)

Operational rule:

- do not use V4.2 as the primary implementation target when a V4.2.1 document exists for the same topic
- only read V4.2 when a V4.2.1 document explicitly points back to it

## Archived Design History

These documents are retained for historical traceability and architectural evolution, not for current implementation:

- `2026-03-26-overnight-agent-loop-design.md`
- `2026-03-26-overnight-agent-loop-design-v2.md`
- `2026-03-27-overnight-agent-loop-design-v3.md`
- `2026-03-27-nightshift-v4-unified-spec.md`
- `2026-03-27-nightshift-v4-unified-spec.zh-CN.md`
- `2026-03-27-nightshift-v4.2-unified-spec.zh-CN.md`

## Context Hygiene Rule

When reading specs for implementation work:

- default to the V4.2.1 reading path only
- do not preload older specs “just in case”
- consult legacy documents only when resolving an explicit inheritance or design-history question

This keeps the active context small while preserving traceability.
