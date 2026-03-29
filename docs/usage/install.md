# Install

NightShift currently requires:

- Python `3.12` or newer
- Git
- the engine binary you intend to use, available on `PATH`

The current MVP registry uses the `codex` and `claude` adapters. Install the corresponding engine binaries for the environment you plan to run.

## Install NightShift

From the repository root:

```bash
python -m pip install -e .
```

If you work with multiple checkouts or editable installs, read [../local-development.md](../local-development.md) before running commands from another worktree.

## Verify The Install

Start with the CLI help:

```bash
nightshift --help
```

If your shell does not expose the installed console script yet, the equivalent form is:

```bash
python -m nightshift.cli.main --help
```

If you want a repository-level sanity check, run:

```bash
python -m pytest -v
```

For a quick product smoke check, the queue and run commands are the most useful next step:

```bash
nightshift queue status --repo /path/to/repo
nightshift run --issues NS-123 --config /path/to/repo/nightshift.yaml
```

If the repository has already migrated to Phase 1 layered project config, commands that take `--repo` can resolve config from the repository root and omit `--config`, for example:

```bash
nightshift run-one ISSUE-1 --repo /path/to/repo
nightshift queue add NS-123 --repo /path/to/repo
```
