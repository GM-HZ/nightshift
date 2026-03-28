# NightShift Architecture

This directory is the current architecture entry point for the repository.

It exists to separate two different questions that were previously mixed together:

- what part of NightShift is already implemented and verified
- what part of NightShift still belongs to the broader product workflow

This directory is a working architecture view, not a declaration that the current Python package layout is final.

Its purpose is to make the next design and implementation steps easier to reason about.

## Current Status

- kernel: implemented and verified
- product workflow: partially designed, not fully implemented

## Boundary Confidence

The `kernel` vs `product workflow` split should currently be read as a planning and ownership boundary.

It is grounded in the `v4.2.1` architecture, but it is still a working agreement.

It does not yet imply that every source directory or module has been permanently classified.

## Reading Guide

Start here when you need to understand the current system boundary:

- [kernel/README.md](./kernel/README.md)
- [product/README.md](./product/README.md)

## Relationship To The Spec Set

The full design history and the active `v4.2.1` spec set still live under:

- `docs/superpowers/specs/`

Use this `docs/architecture/` directory as the shortest route to the current architectural picture.

Use `docs/superpowers/specs/` when you need the full normative design detail or design history.
