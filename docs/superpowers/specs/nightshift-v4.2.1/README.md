# NightShift V4.2.1 Detailed Design Pack

This directory contains the patch-level detailed design documents for NightShift V4.2.1.

Canonical entry point for implementation work:

- [../README.md](../README.md)

- Parent patch spec:
  [../2026-03-27-nightshift-v4.2.1-unified-spec.md](../2026-03-27-nightshift-v4.2.1-unified-spec.md)
- Base spec inherited where unchanged:
  [../2026-03-27-nightshift-v4.2-unified-spec.md](../2026-03-27-nightshift-v4.2-unified-spec.md)

## Patch Scope

V4.2.1 revises the documents needed to close the remaining implementation seams:

- immutable contract vs mutable runtime state
- persistence source of truth
- minimum kernel interfaces for recovery, reporting, and queue runtime operations
- recovery normalization after crash or restart
- artifact layout vs authoritative record layout
- splitter proposal normalization into immutable issue contracts
- minimal kernel report vs richer report generator phasing

## Reading Order

1. `01-domain-model.md` - revised in V4.2.1
2. `02-kernel-interfaces.md` - revised in V4.2.1
3. `03-state-machines.md` - revised in V4.2.1
4. `04-engine-adapters-and-workspaces.md` - revised in V4.2.1
5. `05-requirement-splitter-and-context-loading.md` - revised in V4.2.1
6. `06-cli-config-persistence-alerting.md` - revised in V4.2.1
7. `07-language-and-phasing.md` - revised in V4.2.1

## Inheritance Rule

V4.2.1 supersedes V4.2 where a V4.2.1 document exists.

Implementation rule:

- use this pack as the default detailed design source
- only open V4.2 documents when a V4.2.1 document explicitly delegates to them

## Why A Patch-Level Pack

V4.2 already established the correct product workflow and kernel direction.

V4.2.1 does not replace that architecture with a new one. It only tightens the parts that were still underspecified for implementation:

- contract boundary
- state and persistence truth model
- interface sufficiency
- recovery normalization
- artifact layout
- proposal normalization
- phasing/report semantics
