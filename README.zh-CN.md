# NightShift

[English README](./README.md)

NightShift 是一个夜间 AI 编码执行 harness。当前仓库同时包含 `v4.2.1` 架构规格文档，以及一个 Python MVP kernel。这个 kernel 已经可以执行单个 issue、运行验证、恢复中断执行，并生成最小历史报告。

## 当前状态

- 当前实现目标：`v4.2.1`
- 当前 CLI 命令面：`run-one`、`recover`、`report`、`queue status`、`queue show`、`queue reprioritize`
- 当前引擎适配器：`codex`、`claude`
- 当前范围：单 issue 执行流程，以及持久化、验证、恢复、基于 run 的报告

## 仓库结构

- `src/nightshift/`：Python MVP kernel 实现
- `tests/`：可执行行为测试与回归覆盖
- `examples/`：配置和 issue contract 的参考形状
- `docs/superpowers/specs/`：架构历史和当前规格集合
- `docs/mvp-walkthrough.md`：当前 MVP 的实现使用说明
- `docs/2026-03-28-workflow-verification-report.md`：真实 operator rehearsal 结果和已确认的 workflow gap
- `docs/local-development.md`：多 worktree 本地开发时的安全执行说明

## 当前推荐入口

- 规格索引：`docs/superpowers/specs/README.md`
- 当前统一架构：`docs/superpowers/specs/2026-03-27-nightshift-v4.2.1-unified-spec.md`
- 当前详细设计包：`docs/superpowers/specs/nightshift-v4.2.1/README.md`
- MVP walkthrough：`docs/mvp-walkthrough.md`
- 最新 workflow 验证报告：`docs/2026-03-28-workflow-verification-report.md`
- 本地开发说明：`docs/local-development.md`

## 当前 MVP 边界

当前已经可用的能力：

- 加载 `nightshift.yaml`
- 读取 immutable issue contract 和 current issue record
- 创建 issue worktree 和 snapshot
- 通过单一选定的引擎适配器执行：`codex` 或 `claude`
- 运行 validation gate
- 持久化 run state、issue snapshot、attempt record、event 和 alert
- 将中断执行恢复到新的 controlling run
- 从 run 级持久化历史生成最小报告

当前引擎选择语义：

- 每次 `run-one` 只选择一个 engine
- 选择顺序是 `IssueContract.engine_preferences.primary`，否则 `runner.default_engine`
- `engine_preferences.fallback` 和 `runner.fallback_engine` 当前仍保留在 schema 中，但 MVP harness 不会自动切换
- 如果选中的 engine 失败，operator 应该直接查看持久化的 attempt record 和 artifact

当前明确不在 MVP 内的内容：

- requirement splitter
- PR dispatcher / merge automation
- notifications 和 dashboard
- 超出当前 queue primitives 之外的 unattended 多 issue 夜跑调度策略

## 剩余的非 MVP gap

当前分支有意不是一个完整的 `v4.2.1` 产品实现。下面这些缺口是已知范围外内容，不属于“当前 MVP 做漏了”的 bug：

- 还没有 issue ingestion 流程：执行前仍需要先 seed contract 和 current issue record
- 还没有多 issue 的 overnight control loop：目前只有 `run-one`，还没有 `run`、`run --daemon`、`stop`
- 还没有 queue admission 命令：`queue add` 仍未实现
- 还没有 delivery automation：branch handoff、PR 打开、review 同步、merge 流程还没接上
- 还没有 operator log 视图：`logs --issue` 未实现
- `retry`、`alerts`、以及顶层 validation command groups 这些配置面已经建模，但在 MVP 里只接了最小实现
- 还没有 richer morning report generator，目前只有最小 JSON 历史报告

## 本地验证

```bash
python -m pytest -v
```

如果你在多个 worktree 或多个 editable install 之间切换，请先阅读 `docs/local-development.md`，优先使用显式 `PYTHONPATH` 配合明确的解释器路径。
