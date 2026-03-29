# NightShift Local Development

This note is for contributors working on NightShift itself.
It covers the safest way to run tests and CLI commands locally when multiple worktrees or editable installs exist on the same machine.

## Why This Matters

During workflow rehearsal, one run accidentally executed code from an older editable install instead of the current checkout. The command looked valid, but the Python environment was still bound to a different worktree.

If you are switching between:

- `/Users/gongmeng/dev/code/nightshift`
- `/Users/gongmeng/dev/code/nightshift/.worktrees/...`

you should assume that `python -m ...` can silently import the wrong source tree unless you control both the interpreter and the import path.

## Recommended Rule

For local verification, always make the active checkout explicit.

Use one of these patterns:

### Option 1: repo-local virtualenv per checkout

Recommended when you actively develop in more than one worktree.

```bash
cd /path/to/active/checkout
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pytest -v
```

This keeps the interpreter and editable install aligned with the checkout you are currently editing.

### Option 2: explicit `PYTHONPATH` with a known interpreter

Recommended when you want to reuse an existing dependency environment but force imports to come from the active checkout.

```bash
PYTHONPATH=/path/to/active/checkout/src \
PATH="/path/to/known/venv/bin:$PATH" \
python -m pytest -v
```

This is the safest shared-environment pattern for this repository.

## Recommended Commands For This Repository

When working from `/Users/gongmeng/dev/code/nightshift`, the safest explicit form is:

```bash
PYTHONPATH=/Users/gongmeng/dev/code/nightshift/src \
PATH="/Users/gongmeng/dev/code/nightshift/.worktrees/nightshift-v4.2.1-mvp/.venv/bin:$PATH" \
python -m pytest -v
```

And the equivalent CLI form is:

```bash
PYTHONPATH=/Users/gongmeng/dev/code/nightshift/src \
PATH="/Users/gongmeng/dev/code/nightshift/.worktrees/nightshift-v4.2.1-mvp/.venv/bin:$PATH" \
python -m nightshift.cli.main --help
```

If the active checkout changes, update the `PYTHONPATH` first.

## What To Avoid

- do not assume `python -m ...` is using the checkout in your current shell directory
- do not reuse an old editable install without checking where it points
- do not trust a passing command if the behavior looks inconsistent with the code you just edited

## Quick Sanity Check

If local behavior looks wrong, verify these before debugging application logic:

1. Which interpreter is running?
2. Which checkout does `PYTHONPATH` point at?
3. Was `pip install -e .` last run from this checkout or a different worktree?

If any of those are unclear, fix the environment first and rerun the command before changing code.
