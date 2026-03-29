# Workflow

This page describes the live operator flow in the current repository state.

NightShift still has a broader product direction in the design docs, but this page stays aligned with the code that actually exists today.

## Current Flow

`GitHub issue -> issue ingest-github -> approved work order -> queue add -> run --issues|run --all|run --all --daemon -> deliver --issues -> recover/report`

## Step By Step

### Planning Entry

NightShift now has a live GitHub-based planning bridge:

```bash
nightshift issue ingest-github \
  --repo-full-name GM-HZ/nightshift \
  --issue 42 \
  --repo /path/to/repo \
  --config /path/to/repo/nightshift.yaml
```

This command:

- fetches a compliant GitHub issue
- validates provenance and template expectations
- bridges it into `.nightshift/work-orders/WO-GH-<n>.md`

It does **not** freeze a contract by itself. The resulting work order still flows through `queue add`.

The broader `requirement -> proposal -> issue -> delivery` chain still exists in design and historical rehearsal evidence, but only the GitHub issue bridge is live in the current CLI surface.

### Queue Add

The issue enters the execution queue.

This is also the current freeze point.

At `queue add` time, NightShift:

- reads the current approved Work Order
- materializes an immutable `IssueContract`
- records the frozen work order revision
- freezes approved execution context including `non_goals` and `context_files`
- admits the issue into the runnable queue only if that materialization succeeds

If the Work Order changes after that, the issue must go through `queue add` again before `run` should be trusted to use the newer semantics.

Current queue operations are available through the CLI:

```bash
nightshift queue add NS-123 --repo /path/to/repo --config /path/to/repo/nightshift.yaml
nightshift queue status --repo /path/to/repo
nightshift queue show NS-123 --repo /path/to/repo
nightshift queue reprioritize NS-123 high --repo /path/to/repo
```

`queue show` now also surfaces the frozen contract context in lightweight form, including `non_goals_count` and `context_files`.

### Run

NightShift currently exposes product-facing batch execution through `run`.

The live commands are:

```bash
nightshift run --issues NS-123,NS-124 --repo /path/to/repo --config /path/to/repo/nightshift.yaml
nightshift run --all --repo /path/to/repo --config /path/to/repo/nightshift.yaml
nightshift run --all --daemon --repo /path/to/repo --config /path/to/repo/nightshift.yaml
```

`run` executes sequentially and fails fast. It reuses the existing kernel execution path for each selected issue.

The current unattended control slice is:

- `run --all --daemon`
- `stop`

The daemon loop is still conservative:

- sequential
- fail-fast
- stop-aware between issues
- no pause/resume
- no continue-on-failure
- no slot-aware scheduling

`run-one` still exists as the lower-level kernel command for a single issue:

```bash
nightshift run-one NS-123 --repo /path/to/repo --config /path/to/repo/nightshift.yaml
```

Both paths write durable run state, attempts, and artifacts.

### Deliver

NightShift now has a live explicit delivery command:

```bash
nightshift deliver --issues GH-7 --repo /path/to/repo --config /path/to/repo/nightshift.yaml
```

This command:

- only accepts already accepted issues
- requires a frozen accepted delivery snapshot
- pushes the issue branch
- opens a draft PR
- writes delivery linkage back to the current issue record

This is still a conservative first delivery slice. Richer delivery policy, merge automation, and PR update/reopen behavior are still design work.

### Recover And Report

Recovery and reporting are also live today:

```bash
nightshift recover --run RUN-123 --repo /path/to/repo
nightshift report --repo /path/to/repo --config /path/to/repo/nightshift.yaml
```

`report` remains minimal and historical, not a rich operator report layer.

## What Is MVP-Shaped Today

- the live operator surface is still narrower than the broader product design direction
- queue admission and work-order freeze are live
- batch execution is live, but still sequential and fail-fast
- explicit delivery is live, but still conservative
- unattended overnight control is live, but still MVP-shaped
- reporting is still minimal
- the `.nightshift` migration is phased and compatibility-first

## What Is Design Direction, Not Live CLI

These are still important NightShift product directions, but should currently be read as design work rather than active commands:

- splitter / proposal review CLI
- richer overnight policies such as pause/resume, continue-on-failure, and slot-aware scheduling

## What To Use For Verification

If you want to confirm the current live baseline, start with:

- [../architecture/coverage/current-capability-truth-matrix.md](../architecture/coverage/current-capability-truth-matrix.md)
- run the queue, batch run, and kernel commands described above

If you want the historical end-to-end rehearsal evidence for the broader product chain, start with:

- [../2026-03-28-workflow-verification-report.md](../2026-03-28-workflow-verification-report.md)
- [../rehearsals/2026-03-29-gh7-product-e2e/README.md](../rehearsals/2026-03-29-gh7-product-e2e/README.md)
