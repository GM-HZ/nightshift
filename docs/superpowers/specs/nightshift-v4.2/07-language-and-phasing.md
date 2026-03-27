# 07. Language And Phasing

## Language Recommendation

The current recommendation is:

- use **Python** for the NightShift kernel and CLI harness
- optionally add **TypeScript** later for dashboard or web control plane work

## Why Python For The Kernel

The NightShift kernel is primarily:

- subprocess orchestration
- filesystem manipulation
- YAML and JSON handling
- repository scanning
- state machine execution
- CLI glue code

That favors Python because the core implementation surface is operational and orchestration-heavy rather than UI-heavy.

## Why Not TypeScript For MVP

TypeScript can absolutely implement NightShift, but for MVP it introduces more ceremony in a place where the main work is:

- invoking external CLIs
- managing worktrees
- reading and writing state
- normalizing command results

Those jobs are better served by keeping kernel code friction low.

## When TypeScript Makes Sense

TypeScript becomes more compelling when NightShift gains:

- a dashboard
- a web control plane
- richer frontend interactions
- external user-facing service layers

At that point a split architecture is reasonable:

- Python kernel
- TypeScript UI or control surface

## Suggested Python Stack

- CLI:
  - `typer` or standard-library `argparse`
- data models:
  - `pydantic`
- persistence:
  - JSON, YAML, NDJSON
- process management:
  - `subprocess` and `asyncio`
- path management:
  - `pathlib`

## Delivery Phasing

### Phase 1: Kernel Skeleton

- domain model
- state store
- issue registry
- run orchestrator shell
- workspace manager

### Phase 2: Engine And Validation

- Codex adapter
- Claude Code adapter
- validation gate
- rollback and retry logic

### Phase 3: Product Workflow

- requirement splitter
- report generator
- notifications
- PR dispatcher

### Phase 4: Expansion

- dashboards
- provider integrations
- dependency-aware scheduling
- parallel execution

## Phasing Rule

Do not build edge modules before the kernel can:

- run one issue end to end
- reject safely
- recover after interruption
- produce a trustworthy morning report
