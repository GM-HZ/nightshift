# User-Space Operator Environment

## Status

Working product design aligned to `v4.2.1`.

This document defines the first live user-space layer under `~/.nightshift/`.

## Goal

NightShift should stop treating all operator state as either:

- repository-local project config
- ad-hoc environment variables

It needs a first live user-space home for:

- user defaults
- private auth
- machine-local operator settings

## Scope

First live phase only:

- `~/.nightshift/config/user.yaml`
- `~/.nightshift/auth/github.yaml`
- a resolver for user-space root
- precedence wiring into current CLI/config loading
- GitHub-backed commands can use user-space auth as a fallback

Out of scope for the first live phase:

- engine registries under `~/.nightshift/engines/`
- skills/plugins caches
- keychain integrations
- multi-provider auth
- user-space runtime state beyond minimal config/auth

## Root Resolution

Default user-space root:

`~/.nightshift/`

Override for advanced operators/tests:

- `NIGHTSHIFT_HOME`

Resolution order:

1. `NIGHTSHIFT_HOME`
2. `~/.nightshift`

## First Live Files

### User Config

Path:

`~/.nightshift/config/user.yaml`

Purpose:

- user-level defaults that should apply across repositories unless overridden by project config or CLI flags

First live fields:

- `runner.default_engine`
- `runner.fallback_engine`
- `github.default_repo_full_name` (optional helper)

### GitHub Auth

Path:

`~/.nightshift/auth/github.yaml`

Purpose:

- private GitHub auth fallback for GitHub-backed product commands

First live fields:

- `token` (optional)
- `token_env_var` (optional)
- `api_base_url` (optional, default GitHub API)

## Precedence

For operator defaults:

1. CLI flags
2. project config
3. user-space config
4. built-in defaults

For GitHub token resolution:

1. `NIGHTSHIFT_GITHUB_TOKEN`
2. `GITHUB_TOKEN`
3. `~/.nightshift/auth/github.yaml`

This keeps current environment-variable workflows working while giving operators a stable private home.

## Why Keep `token` Support

Long-term, references or keychain integration are preferable.

But for the first live phase, supporting a raw `token` field in `~/.nightshift/auth/github.yaml` is pragmatic because:

- the file is private and not committed
- it reduces friction for real operators
- it matches how many agent tools start before evolving into stronger secret storage

## Current CLI Surfaces That Should Use It

First live integrations:

- `issue ingest-github`
- `deliver --issues`

Both commands currently depend on GitHub credentials and benefit immediately from user-space auth.

## Success Criteria

This phase is successful when:

- NightShift can resolve user-space root deterministically
- project config still wins over user config
- GitHub-backed commands can run without requiring shell env vars every time
- repository-local `.nightshift/` migration remains separate from user-space auth/config
