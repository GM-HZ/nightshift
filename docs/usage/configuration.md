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

If the marker instead declares `project_config_source: compatibility`, NightShift continues to load the root `nightshift.yaml`.

## Queue Add Freeze Point

In the current implementation, `queue add` is also the freeze point for Work Orders:

- NightShift reads the current approved Work Order
- materializes an immutable `IssueContract`
- writes the current frozen contract under `nightshift/issues/`
- preserves revision history under `nightshift/contracts/<issue_id>/`
- freezes approved execution context such as `non_goals` and `context_files`

If the Work Order changes later, a new `queue add` is required so NightShift can freeze a new contract revision.

## Target Direction

The broader long-term model is still split into:

- user space: `~/.nightshift/`
- project space: `<repo>/.nightshift/`

That broader target model is still a design direction in the docs. Do not treat it as the current on-disk layout unless the specific repository has already migrated.

## Practical Rule

Use `nightshift.yaml` for compatibility repositories.
Use the migration marker plus `.nightshift/config/project.yaml` for repositories that have entered Phase 1 layered project config.
