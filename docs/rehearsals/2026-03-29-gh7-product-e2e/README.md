# GH-7 Product E2E Rehearsal Archive

This directory preserves the key artifacts from the end-to-end NightShift product rehearsal that took the Chinese README requirement through the full flow:

`requirement -> split -> publish issue -> ingest -> queue add -> run -> deliver -> PR`

## Outcome

- Source GitHub issue: `GM-HZ/nightshift#7`
- Local issue id: `GH-7`
- Accepted run: `RUN-66c936e1`
- Created PR: `GM-HZ/nightshift#8`
- Final local state: `issue_state=done`, `attempt_state=accepted`, `delivery_state=pr_opened`

## Included Artifacts

- `zh-readme-detailed.md`
  The requirement input used for the rehearsal
- `nightshift.rehearsal.yaml`
  The local config snapshot used for live commands
- `proposal-batch.json`
  The reviewed proposal batch that was published into the GitHub issue template
- `GH-7.yaml`
  The materialized immutable execution contract
- `GH-7.record.json`
  The final mutable issue record after delivery
- `RUN-66c936e1.report.json`
  The accepted run summary produced by NightShift reporting

## Notes

- This archive is intentionally small and human-readable.
- Bulky transient run artifacts and scratch state were cleaned from the repository root after the rehearsal.
- `.worktrees/` were left untouched by this cleanup step.
