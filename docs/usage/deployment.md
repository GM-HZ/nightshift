# Deployment

This page is about rolling NightShift out in a repository or team setting.

It is not server deployment. The current product is a repo-local operator tool with GitHub and engine dependencies.

## Prerequisites

- A GitHub token or equivalent credential source with access to the target repository
- The engine binary for the adapter you plan to run on `PATH`
- A git repository with a working remote and a known default branch
- A NightShift config file for that repository

## Recommended Baseline

Use the current compatibility layout first:

- root `nightshift.yaml`
- repo-local `nightshift/issues/`
- repo-local `nightshift-data/`

Keep the target `~/.nightshift/` and `<repo>/.nightshift/` model in mind as the next-stage direction, but do not assume it is already active unless that repository has been migrated.

When a repository opts into Phase 3 runtime migration, runtime-only state moves under `.nightshift/`:

- `.nightshift/records/current/`
- `.nightshift/records/active-run.json`
- `.nightshift/records/alerts.ndjson`
- `.nightshift/runs/`
- `.nightshift/artifacts/`
- `.nightshift/reports/`

Compatibility repositories continue to use `nightshift-data/` unchanged.

## Branch And PR Assumptions

NightShift expects execution to happen on a branch and to surface reviewable work before merge.

- one execution slice maps to one primary work branch
- the branch should be visible through a draft or reviewable PR
- delivery state is tracked back onto the issue record

## Minimal Rollout Path

1. Configure one repository and one main branch.
1. Make sure the engine binary is installed and reachable.
1. Confirm NightShift can read the repo with `nightshift queue status --repo /path/to/repo`.
1. Run one small issue end to end before broadening usage.
1. Only then expand to more issues or a wider team.

## Practical Notes

- If your team uses multiple worktrees, follow [../local-development.md](../local-development.md) so you do not run the wrong editable install.
- If you are still choosing the repository config shape, start from [../../examples/nightshift.yaml](../../examples/nightshift.yaml) and keep the target layered model separate from the current compatibility layout.
- For report outputs, an explicit `report.output_directory` still overrides the default runtime report root.
