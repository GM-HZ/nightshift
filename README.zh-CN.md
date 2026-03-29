# NightShift

> Language / 语言：[English](README.md) | 简体中文

NightShift 是一个面向夜间运行场景的 AI 编码执行框架。当前仓库同时包含 `v4.2.1` 架构规范集合，以及一个 Python MVP 内核。这个 MVP 已经可以执行单个 issue、运行验证、恢复中断的运行流程，并产出最小化的历史报告。

## 当前状态

- 当前实现目标：`v4.2.1`
- 当前 CLI 命令面：`run-one`、`recover`、`report`、`queue status`、`queue show`、`queue reprioritize`
- 当前引擎适配器：`codex`、`claude`
- 当前范围：单 issue 执行流程，以及持久化、验证、恢复、按 run 范围生成报告

## 仓库结构

- `src/nightshift/`：Python MVP 内核实现
- `tests/`：可执行行为测试与回归覆盖
- `examples/`：配置样例与 issue 合约样例
- `docs/superpowers/specs/`：架构演进历史与当前规范集合
- `docs/mvp-walkthrough.md`：面向实现的当前 MVP 使用说明
- `docs/2026-03-28-workflow-verification-report.md`：真实操作员演练结果与已确认的工作流缺口
- `docs/local-development.md`：多 worktree 场景下的本地安全执行说明
- `docs/architecture/README.md`：当前架构入口，拆分为 kernel 与产品工作流两个视角

## 当前推荐入口

- 规范索引：`docs/superpowers/specs/README.md`
- 当前架构：`docs/superpowers/specs/2026-03-27-nightshift-v4.2.1-unified-spec.md`
- 当前详细设计包：`docs/superpowers/specs/nightshift-v4.2.1/README.md`
- MVP 使用说明：`docs/mvp-walkthrough.md`
- 最新工作流验证：`docs/2026-03-28-workflow-verification-report.md`
- 本地开发说明：`docs/local-development.md`
- 架构入口：`docs/architecture/README.md`

## 当前 MVP 边界

当前已经可用的能力：

- 加载 `nightshift.yaml`
- 读取不可变 issue 合约与当前 issue 记录
- 创建 issue worktree 与快照
- 通过一个选定的引擎适配器执行：`codex` 或 `claude`
- 运行验证门禁
- 持久化 run 状态、issue 快照、attempt 记录、事件与告警
- 将中断的 run 恢复为一个新的控制 run
- 基于 run 范围内的持久化历史生成最小报告

当前引擎选择语义：

- `run-one` 每次 attempt 只选择一个引擎
- 选择顺序是 `IssueContract.engine_preferences.primary`，然后 `runner.default_engine`
- `engine_preferences.fallback` 与 `runner.fallback_engine` 目前仍是预留 schema 字段
- MVP 执行框架在失败后不会自动切换引擎；操作员应直接检查持久化的 attempt 记录与产物

当前 MVP 明确尚未包含的能力：

- requirement splitter
- PR 分发与合并自动化
- 通知与仪表盘
- 超出当前 queue 原语范围之外的无人值守多 issue 夜间调度策略

## 剩余的非 MVP 缺口

当前分支刻意不是一个完整的 `v4.2.1` 产品级实现。下面这些缺口是已知范围，不属于当前 MVP 范围内的 bug：

- 还没有 issue 导入流程：执行前仍需先准备好合约和当前 issue 记录
- 还没有多 issue 夜间控制循环：目前只有 `run-one`，`run`、`run --daemon`、`stop` 尚未实现
- 还没有队列接纳命令：`queue add` 仍然缺失
- 还没有交付自动化：branch 交接、PR 打开、review 同步、merge 工作流尚未接线
- 还没有操作员日志视图：`logs --issue` 尚未实现
- `retry`、`alerts`、顶层验证命令组等配置段已经建模，但在 MVP 中只做了最小接线
- 还没有更丰富的晨间报告生成器，目前只有最小 JSON 历史报告

## 本地验证

```bash
python -m pytest -v
```

如果你在多个 worktree 或多个 editable install 之间工作，请先阅读 `docs/local-development.md`，并优先使用显式的 `PYTHONPATH` 与明确的解释器路径。
