# Configuration

NightShift currently supports two project config modes:

- MVP compatibility mode, which keeps `nightshift.yaml` at the repository root
- Phase 1 layered project config, which uses `.nightshift/config/project.yaml` and a migration marker

## Compatibility Mode

If `.nightshift/config/migration.yaml` is absent, NightShift treats the repository as compatibility mode.

Typical compatibility paths are:

- `nightshift.yaml`
- `nightshift/issues/`
- `nightshift-data/issue-records/`
- `nightshift-data/runs/`
- `nightshift-data/active-run.json`
- `nightshift-data/alerts.ndjson`
- `nightshift-data/reports/`

The compatibility config controls:

- repository location and default branch
- default engine choice
- validation commands
- issue defaults
- retry policy
- worktree and artifact roots
- report output location

A minimal example lives in [../../examples/nightshift.yaml](../../examples/nightshift.yaml).

## Phase 1 Layered Project Config

The Phase 1 layered layout keeps the project config under `.nightshift/config/` and uses a migration marker to make the active mode explicit.

The first layered files are:

- `.nightshift/config/migration.yaml`
- `.nightshift/config/project.yaml`

Example migration marker:

```yaml
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
```

When the marker declares `project_config_source: layered`:

- NightShift loads project config from `.nightshift/config/project.yaml`
- root `nightshift.yaml` is no longer authoritative for that repository
- product-facing CLI paths that accept `--repo` can resolve config from the repository root when `--config` is omitted
- runtime state still remains on the compatibility layout during Phase 1

If the repository also enters Phase 2 contract storage migration, the marker can add:

```yaml
contract_storage_source: layered
```

That moves frozen contracts to:

- `.nightshift/contracts/current/`
- `.nightshift/contracts/history/`

For a repository that has also entered Phase 3 runtime migration, the marker should include:

```yaml
project_config_source: layered
contract_storage_source: layered
runtime_layout_source: layered
```

That moves runtime-only state to:

- `.nightshift/records/current/`
- `.nightshift/records/active-run.json`
- `.nightshift/records/alerts.ndjson`
- `.nightshift/runs/`
- `.nightshift/artifacts/`
- `.nightshift/reports/`

If `report.output_directory` is configured explicitly, that path still wins for report writes. The runtime resolver only supplies the default layered report root.

If the marker instead declares `project_config_source: compatibility`, NightShift continues to load the root `nightshift.yaml`.

## Queue Add Freeze Point

In the current implementation, `queue add` is also the freeze point for Work Orders:

- NightShift reads the current approved Work Order
- materializes an immutable `IssueContract`
- writes the current frozen contract under `nightshift/issues/`
- preserves revision history under `nightshift/contracts/<issue_id>/`
- freezes approved execution context such as `non_goals` and `context_files`

If the Work Order changes later, a new `queue add` is required so NightShift can freeze a new contract revision.

## User-Space Operator Environment

NightShift now has a first live user-space layer under:

- `~/.nightshift/`
- or `NIGHTSHIFT_HOME` when explicitly set

The first live user-space files are:

- `~/.nightshift/config/user.yaml`
- `~/.nightshift/auth/github.yaml`

Current first-phase behavior:

- `issue ingest-github` can use `github.default_repo_full_name` from `user.yaml`
- GitHub-backed commands can resolve auth from `auth/github.yaml` when environment variables are absent

Current precedence remains:

1. CLI flags
2. project config
3. user-space config/auth
4. built-in defaults

Environment variables still win over user-space GitHub auth:

1. `NIGHTSHIFT_GITHUB_TOKEN`
2. `GITHUB_TOKEN`
3. `~/.nightshift/auth/github.yaml`

## Target Direction

The broader long-term model is still split into:

- user space: `~/.nightshift/`
- project space: `<repo>/.nightshift/`

That broader target model is now partially live for user-space config/auth and partially live for migrated project layouts. Do not treat the entire target tree as fully implemented yet.

For migrated repositories, the runtime portion of the project layout lives under `.nightshift/` after the repository has entered layered project config and then opted into Phase 3 runtime migration.

## Practical Rule

Use `nightshift.yaml` for compatibility repositories.
Use the migration marker plus `.nightshift/config/project.yaml` for repositories that have entered Phase 1 layered project config.
