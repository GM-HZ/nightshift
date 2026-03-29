# User-Space Operator Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce the first live `~/.nightshift/` user-space layer so NightShift can resolve user defaults and private GitHub auth outside a repository.

**Architecture:** Add a small user-space resolver rooted at `NIGHTSHIFT_HOME` or `~/.nightshift`, load optional user defaults from `config/user.yaml`, and let GitHub-backed commands fall back to `auth/github.yaml` when environment variables are absent.

**Tech Stack:** Python, existing config loader, existing GitHub-backed bridge/delivery commands, pytest

---

## File Map

- Modify: `src/nightshift/config/models.py`
- Modify: `src/nightshift/config/loader.py`
- Modify: `src/nightshift/product/issue_ingestion_bridge/github_client.py`
- Modify: `src/nightshift/product/delivery/github_client.py`
- Test: `tests/test_config_loader.py`
- Test: `tests/test_issue_ingestion_bridge_service.py`
- Test: `tests/test_delivery_service.py`
- Modify: `docs/usage/configuration.md`
- Modify: `README.md`

---

### Task 1: Add User-Space Root And Models

- [ ] Add config/auth models for minimal user-space support
- [ ] Add resolver for `NIGHTSHIFT_HOME` / `~/.nightshift`
- [ ] Cover with config loader tests
- [ ] Commit

### Task 2: Add User Config Merge

- [ ] Load optional `~/.nightshift/config/user.yaml`
- [ ] Merge user defaults under project config precedence
- [ ] Keep CLI flags as highest precedence
- [ ] Cover with tests
- [ ] Commit

### Task 3: Add GitHub Auth Fallback

- [ ] Teach ingestion bridge and delivery GitHub clients to read `~/.nightshift/auth/github.yaml`
- [ ] Keep env vars ahead of user-space auth
- [ ] Cover with client tests
- [ ] Commit

### Task 4: Sync Docs

- [ ] Update configuration and README docs
- [ ] Clarify first live user-space scope
- [ ] Commit

### Task 5: Final Verification

- [ ] Run focused config/auth regression tests
- [ ] Run full suite: `./.venv/bin/python -m pytest -q`
- [ ] Push branch
