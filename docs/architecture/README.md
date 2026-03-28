# NightShift Architecture

This directory is the current architecture entry point for the repository.

It exists to separate two different questions that were previously mixed together:

- what part of NightShift is already implemented and verified
- what part of NightShift still belongs to the broader product workflow

## Current Status

- kernel: implemented and verified
- product workflow: partially designed, not fully implemented

## Reading Guide

Start here when you need to understand the current system boundary:

- [kernel/README.md](./kernel/README.md)
- [product/README.md](./product/README.md)

## Relationship To The Spec Set

The full design history and the active `v4.2.1` spec set still live under:

- `docs/superpowers/specs/`

Use this `docs/architecture/` directory as the shortest route to the current architectural picture.

Use `docs/superpowers/specs/` when you need the full normative design detail or design history.
