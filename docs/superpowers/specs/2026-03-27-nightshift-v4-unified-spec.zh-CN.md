# NightShift V4.1 统一规格说明

**日期：** 2026-03-27

**状态：** 在 V4 基础上补齐关键接口和生命周期缺口后的统一规格版本。当前作为主设计目标，V1、V2、V3 保留为历史迭代版本。

**一句话定义：** NightShift 是一个面向夜间滚动交付的软件开发 harness：白天由人拆分并确认可自动化执行的 Issue，夜间由 NightShift 调度 Codex CLI 或 Claude Code CLI 执行，独立完成验证，并在第二天早晨把可审查的分支或 PR 交给人类处理。

---

## 1. 文档目的

这份文档把之前分散的两种视角统一起来：

- `nightshift.md` 中偏 PRD / 产品工作流的视角
- V3 中偏 harness / kernel 执行纪律的视角

NightShift 要同时满足两件事：

1. 作为产品，流程和价值主张要容易被理解。
2. 作为系统，内核约束必须足够严格，才能支撑无人值守的夜间执行。

因此，这份文档明确区分：

- **产品层**：NightShift 是什么、用户如何使用、整体工作流如何运转
- **内核层**：NightShift 在执行时必须遵守的系统约束、验证规则、隔离规则与状态规则

---

## 2. 产品愿景

### 2.1 Slogan

让软件交付像夜班流水线一样运转：白天由人拆分和确认工作，NightShift 整晚执行和验证，第二天由人 review 结果。

### 2.2 产品定位

NightShift 是一个围绕强大 AI 编码引擎构建的轻量工作流外壳。

它**不试图替代**：

- Codex CLI
- Claude Code CLI
- 仓库自身的 CI
- 人类代码评审

它**真正提供**的是：

- 从需求到 Issue 的拆分工作流
- 自动化执行准入判断
- Issue 队列执行
- 隔离的编码工作空间
- 独立的结果验证
- 重试与驳回机制
- PR / review handoff 产物
- 夜间运行报告

### 2.3 产品边界

NightShift 不是：

- 通用 Agent 平台
- 多 Agent 研究系统
- 自动合并机器人
- 产品决策或架构决策的替代者

NightShift 是：

- 一个 AI coding harness
- 面向 issue 粒度的工作
- 在人类审批前提下运行
- 以强验证和强约束保证输出质量

---

## 3. 用户工作流

NightShift 的完整流程分为三个阶段。

### 3.1 阶段 A：白天准备

此时人类在场。

工作流如下：

1. 人提供一个较大的需求、一个 backlog 区域，或一组需要推进的问题。
2. NightShift 协助把它拆成多个 issue 粒度的任务。
3. 人审阅系统给出的 issue 拆分结果。
4. 人可以确认、修改、删除，或补充 issue。
5. 已确认的 issue 被规范化成可执行的 issue contract。
6. 夜间执行队列被建立。

### 3.2 阶段 B：夜间执行

此时 NightShift 无人值守运行。

工作流如下：

1. 选取下一个已经通过自动化准入的 issue。
2. 创建独立的分支和隔离 worktree。
3. 选择执行引擎。
4. 将 issue 下发给 Codex CLI 或 Claude Code CLI。
5. 运行独立验证。
6. 若验证通过，则保留结果并准备 PR 或 review artifact。
7. 若验证失败，则根据策略进行驳回、重试或挂起。
8. 持续执行，直到队列耗尽、运行预算耗尽，或安全阈值被触发。

### 3.3 阶段 C：早晨审查

人类重新回到流程中，作为最终决策者。

工作流如下：

1. 查看夜间运行报告。
2. 按优先级检查已通过验证的分支或 PR。
3. 查看被挂起 issue 的阻塞说明与交接信息。
4. 决定 merge、要求后续跟进，或丢弃结果。

---

## 4. 核心产品叙事

NightShift 面向团队的产品叙事应该是：

- 白天，人负责理解需求并确认任务边界。
- 夜里，NightShift 按 issue 粒度逐个推进这些任务。
- 具体的编码工作由现成的 AI 编码引擎完成。
- NightShift 独立判断这些结果是否真的可接受。
- 到第二天早上，团队面对的是一批可 review 的结果，而不是一堆还没开始的任务。

这就是 NightShift 的产品承诺。下面的内核规则，都是为了让这份承诺可信。

---

## 5. 总体架构

NightShift 由三层组成。

### 5.1 产品层

面向用户与操作者的工作流：

- requirement splitting
- issue queue management
- run control
- report generation
- PR 与 review handoff

### 5.2 Harness 内核层

负责执行控制与系统安全：

- issue 准入
- context 打包
- engine dispatch
- validation authority
- rollback / rejection
- workspace isolation
- authoritative state

### 5.3 人类治理层

人类保留以下权力：

- 判断哪些工作适合自动化
- 判断 issue 拆分是否合理
- 判断已接受结果是否应当 merge
- 对产品或架构模糊地带做最终决策

---

## 6. 基本系统规则

NightShift 遵循这条基本规则：

> Harness 负责治理，Execution Engine 负责执行，人类负责审批。

这条规则用来避免角色混淆：

- Codex CLI 和 Claude Code CLI 是执行引擎
- NightShift 是控制平面
- 人类是治理层和 merge gate

---

## 7. 内核原则

下面这些是不可妥协的实现原则。

1. **没有可执行验证，就没有 execution issue**
   如果一个任务无法被程序化校验，它就不能进入无人值守的自动执行环。

2. **执行引擎不是最终裁判**
   引擎可以执行、解释、总结，但 NightShift 才有 acceptance / rejection 的最终判断权。

3. **一个 issue，对应一个 branch 和一个隔离 worktree**
   执行结果必须可审查、可丢弃、可恢复。

4. **失败尝试必须容易驳回**
   驳回、回滚、轮转不是异常情况，而是系统的正常行为。

5. **持续性状态必须保存在文件里，而不是聊天上下文里**
   夜间长时间运行不能依赖无限膨胀的 conversation history。

6. **进入自动化和最终 merge 都必须有人类把关**
   NightShift 可以自动执行，但不能代替最终治理。

---

## 8. 角色与职责

### 8.1 NightShift Harness

Harness 负责：

- issue 规范化
- readiness check
- 队列管理
- branch 与 worktree 创建
- context 打包
- engine 调度
- 独立验证
- 重试与挂起决策
- authoritative run state
- authoritative issue state
- 报告生成
- PR / review handoff 产物生成

### 8.2 Execution Engine

当前的执行引擎包括：

- Codex CLI
- Claude Code CLI

它们负责：

- issue 局部代码理解
- issue 局部编码实现
- 在 issue 范围内做局部调试
- 产出候选修改
- 输出结构化执行结果

它们不负责：

- acceptance authority
- 队列策略
- 长生命周期状态
- merge 决策

### 8.3 Humans

人类负责：

- 理解真实需求意图
- 审核 issue 拆分
- 决定哪些 issue 可进入自动化
- 决定 merge 或 reject
- 在产品或架构问题不明确时做最终判断

---

## 9. Issue 分类

NightShift 支持多种 issue 类型，但并不是所有 issue 都能直接夜间执行。

### 9.1 Execution Issue

适合无人值守自动执行。

要求：

- 存在可执行验证
- 范围有边界
- 路径约束明确
- 测试权限明确
- 已被人类批准进入自动化

### 9.2 Planning Issue

过大、过模糊，不能直接执行。

用途：

- 拆分成更小的 issue

### 9.3 Repro Issue

目前还不能直接修，因为缺少稳定的验证方式。

用途：

- 建立复现脚本
- 建立可执行验收条件
- 完成后升级为 execution issue

### 9.4 Investigation Issue

以诊断和分析为主，而不是直接保留代码结果。

用途：

- 输出结构化结论
- 解释阻塞原因
- 提出后续 execution issues

---

## 10. Issue 准入规则

下面这条规则是强制性的：

> 没有可执行验证，就没有 execution issue。

可接受的程序化验证方式包括：

- issue 级测试命令
- 稳定的复现脚本
- 机器可读的检查器
- 带明确字段的 JSON 输出
- 输出或 schema 匹配规则

没有这些验证方式的任务，只能停留在：

- planning
- repro
- investigation

而不能进入夜间无人值守执行队列。

---

## 11. Issue Contract

Issue contract 是 NightShift 的核心输入单元。

建议 schema 如下：

```yaml
id: 123
title: 修复 session store 中的 cache invalidation race
kind: execution
priority: high
engine_preferences:
  primary: codex
  fallback: claude_code
goal: 防止并发失效场景下读到过期 session 数据。
description: >
  当前 invalidation 逻辑在并发场景下可能导致 stale read。
acceptance:
  - invalidation 的确定性测试通过
  - core regression suite 通过
allowed_paths:
  - src/session/
  - tests/session/
forbidden_paths:
  - migrations/
  - infra/
verification:
  issue_validation:
    required: true
    commands:
      - pytest tests/session/test_invalidation.py -q
    pass_condition:
      type: exit_code
      expected: 0
  static_validation:
    required: false
    commands:
      - ruff check src/session tests/session
      - mypy src/session
    pass_condition:
      type: all_exit_codes_zero
  regression_validation:
    required: true
    commands:
      - pytest tests/session/test_smoke.py -q
      - pytest tests/api/test_login.py -q
    pass_condition:
      type: exit_code
      expected: 0
  promotion_validation:
    required: false
    commands: []
    pass_condition: null
test_edit_policy:
  can_add_tests: true
  can_modify_existing_tests: true
  can_weaken_assertions: false
  requires_test_change_reason: true
attempt_limits:
  max_files_changed: 3
  max_lines_added: 80
  max_lines_deleted: 40
timeouts:
  command_seconds: 600
  issue_budget_seconds: 3600
risk: medium
status: ready
notes: 只修 invalidation race，不要顺手重构整个存储实现。
last_attempt_summary: ""
```

### 必填字段

- `id`
- `title`
- `kind`
- `priority`
- `goal`
- `allowed_paths`
- `forbidden_paths`
- `verification`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`
- `status`

### 面向产品层的字段

- `description`
- `acceptance`
- `notes`
- `risk`

### 面向内核层的字段

- `engine_preferences`
- `allowed_paths`
- `forbidden_paths`
- `verification`
- `test_edit_policy`
- `attempt_limits`
- `timeouts`

---

## 12. Requirement Splitter

Requirement splitter 属于产品层能力。

### 12.1 目的

帮助人把一个较大的需求拆成 issue 粒度的工作单元。

### 12.2 工作方式

1. 读取基础仓库上下文。
2. 调用 AI 引擎提出 issue 拆分方案。
3. 向人展示拆分结果。
4. 允许确认、修改、删除或新增 issue。
5. 将审核通过的 issue 保存为规范化格式。

### 12.3 拆分规则

拆分器应该尽量产出满足以下条件的 issue：

- 可独立实现
- 可独立验证
- 修改范围小且明确
- 尽量减少 issue 间代码依赖

### 12.4 治理规则

AI 可以提出 issue 拆分建议，但只有被人审核通过的 issue 才能进入执行队列。

### 12.5 Repo Context 获取策略

“读取基础仓库上下文” 不是实现细节，而是影响拆分质量与 token 成本的一等设计问题。

NightShift 应按分层方式获取 repo context。

#### Layer 0：低成本元信息

默认总是读取：

- 顶层文件树摘要
- 主要语言与框架信号
- 构建或包管理文件
- README 与高信号文档
- 测试目录分布
- 如存在则读取 CI 配置摘要

#### Layer 1：相关锚点

基于需求关键词与仓库信号读取：

- 可能相关的目标模块
- 可能的入口文件
- 邻近测试文件
- 如可得，则读取近期修改热点

#### Layer 2：聚焦深读

只在确实影响拆分质量时深入读取：

- 具体实现文件
- 局部调用链
- schema / API 定义
- 领域设计文档

#### Layer 3：可复用摘要

把高成本读取后的压缩摘要保留下来，避免重复拆分时每次都重新扫描整个仓库。

#### Splitter Context 规则

Splitter 不能无差别读取整个仓库，必须在明确的 file budget 和 token budget 下工作。

---

## 13. 队列模型

NightShift 需要一个规范化 issue 队列。

建议状态包括：

- `draft`
- `ready`
- `running`
- `validating`
- `accepted`
- `pr_opened`
- `retryable`
- `blocked`
- `deferred`
- `done`

### 13.1 `blocked` 与 `deferred` 的语义区分

这两个状态必须严格区分。

- `blocked`
  表示 issue 在当前条件下无法继续推进，必须等待外部变化。
  常见原因：
  - 需要人做决策
  - 需要触碰 forbidden path
  - 环境配置异常
  - 出现 repeated semantic failure
  - 缺少依赖或凭证

- `deferred`
  表示 issue 并非做不了，而是被 harness 有意延后处理。
  常见原因：
  - 优先级低于其他 ready issue
  - 当夜剩余预算不足
  - 依赖预计稍后才会满足
  - promotion validation 被延后
  - 队列整形或批处理策略

操作规则：

- `blocked` 通常需要人工或外部条件变化后才能恢复
- `deferred` 可以在没有人工介入的情况下稍后自动回到队列

建议支持的队列操作：

- add issue
- inspect issue
- reprioritize issue
- mark blocked
- resume issue
- remove issue

队列既属于产品工作流的一部分，也是内核控制状态的一部分。

---

## 14. 执行生命周期

对于每一个 execution issue：

1. 选取下一个 `ready` 的 issue。
2. 创建或恢复隔离 branch 与 worktree。
3. 执行 pre-flight 检查。
4. 打包执行上下文。
5. 调度所选引擎。
6. 收集引擎输出。
7. 运行独立验证。
8. 做出 accept / reject / retry / suspend 决策。
9. 更新 authoritative state。
10. 继续当前 issue 或轮转下一个。

---

## 15. Context 打包

NightShift 应把 context 分成四层。

### 15.1 Policy Context

稳定规则：

- `program.md`
- NightShift 配置
- 输出格式约束
- anti-cheating rules
- validation rules

### 15.2 Issue Context

只包含当前 issue：

- issue contract
- goal
- description
- acceptance
- 路径约束
- test edit policy
- attempt limits
- branch 与 worktree 元数据
- 最近几次 attempt 的摘要

### 15.3 Code Context

只包含当前 issue 相关代码：

- 目标源码文件
- 目标测试文件
- 最近失败位置
- 如有需要，加入之前被接受或驳回的 diff

### 15.4 Run Context

只注入压缩后的运行态信息：

- 已使用的 attempts
- 剩余预算
- 最近失败指纹
- 必要时的队列摘要

### 15.5 Context 规则

执行引擎不能依赖整晚累积的聊天上下文。

NightShift 必须通过结构化状态文件维持连续性。

---

## 16. Engine Adapter 模型

NightShift 应定义稳定的引擎适配接口。

建议逻辑接口如下：

- `prepare(issue_contract, workspace, context_bundle)`
- `execute()`
- `collect_result()`
- `normalize_output()`

### 16.1 Engine 错误契约

Adapter 契约不能只定义成功路径，还必须定义失败语义。

每次 engine invocation 都应该被归一化为结构化结果，而不是把异常边界直接暴露给 harness。

建议的归一化结果类型：

- `success`
- `engine_timeout`
- `engine_crash`
- `partial_output`
- `invalid_output`
- `interrupted`
- `environment_error`

每种结果至少应包含：

- engine name
- invocation id
- exit code（如有）
- start time
- end time
- duration
- stdout artifact path
- stderr artifact path
- raw transcript / log artifact paths（如有）
- recoverable flag
- engine error type
- summary message

### 16.2 Adapter 边界规则

Adapter 可以捕获引擎原生异常，但必须在返回给 harness 前完成归一化。

Harness 不应依赖 engine-specific exception parsing 来决定是否：

- retry
- fallback 到其他引擎
- 标记 infra failure
- suspend issue

V4 支持的引擎：

- `codex`
- `claude_code`

未来可以继续新增其他引擎，而不需要改动 harness 主契约。

---

## 17. 验证模型

验证属于内核层的 acceptance gate。

### 17.1 Issue Validation

直接验证 issue 目标是否达成。

### 17.2 Static Validation

可选的仓库静态检查：

- lint
- typecheck
- build

### 17.3 Regression Validation

保护关键已有行为不被破坏。

### 17.4 Promotion Validation

用于更高门槛的验证，例如：

- PR readiness
- nightly wrap-up
- 高置信度候选分支

### 17.5 默认策略

- issue validation 必须执行
- regression validation 必须执行
- static validation 在成本可接受时建议执行
- promotion validation 可选

---

## 18. 验证裁决权

NightShift 必须通过程序化检查来决定 acceptance，例如：

- exit code
- 结构化输出
- 测试数量变化
- 输出匹配
- schema 校验

执行引擎可以解释失败原因、辅助分析日志，但不能作为主 acceptance judge。

### 关于 AI as Judge 的限制

如果产品层场景里存在自然语言 test case 或文字描述，AI 判断只能用于：

- 辅助反馈
- triage 帮助
- issue refinement 支持

不能作为夜间无人值守 acceptance 的主门禁。

这是一个明确的设计取舍。

---

## 19. Workspace 隔离

每个 execution issue 都必须拥有：

- 一个 branch
- 一个隔离 worktree

推荐 branch 命名：

```text
nightshift/issue-<id>-<slug>
```

推荐 worktree 目录：

```text
.nightshift/worktrees/issue-<id>/
```

用户平时使用的主工作区不能作为无人值守执行表面。

---

## 20. Pre-Flight

在调度引擎前，NightShift 必须检查：

- worktree 是否干净
- branch / worktree 是否正确
- 环境是否就绪
- 必要服务是否可用
- baseline validation 是否健康

如果 pre-flight 失败，就不能调度引擎。

应该：

- 分类 blocker
- 更新状态
- 按策略轮转或停止

---

## 21. Attempt 限制

Attempt 的规模必须由 harness 检查，而不是只靠 prompt 提醒。

检查项包括：

- 路径范围
- 文件数量
- 行数变化
- 是否触碰 forbidden path

若 attempt 超出阈值：

- 直接 reject
- 标记为 scope risk 或 scope expansion
- 必要时带更严格约束重新调度

---

## 22. 驳回与回滚

在每次 attempt 前，NightShift 必须记录：

- branch
- worktree
- pre-edit commit SHA

若 attempt 被驳回：

- 回滚由 harness 控制
- 清理由隔离 worktree 内完成
- 只有明确白名单产物可以保留

被驳回的尝试不能污染后续 attempt。

---

## 23. 重试模型

重试存在的意义是恢复“便宜失败”，而不是为无限循环找借口。

建议策略：

- 只有在失败看起来局部且可恢复时才重试
- 必须有明确的重试上限
- 一旦识别出 repeated semantic failure，就应停止重试

重试策略可以包括：

- 把失败输出追加进 context
- 更强调 path constraints
- 缩小到最关键的 acceptance 条件

但重试的预算和策略必须由 harness 控制。

---

## 24. 失败分类

建议使用以下 blocker / failure 类型：

- `infra_blocked`
- `dirty_baseline`
- `flaky_validation`
- `scope_expansion`
- `scope_expansion_risk`
- `forbidden_path_required`
- `needs_human_decision`
- `repeated_semantic_failure`
- `environment_misconfigured`

更细粒度的失败分类有利于第二天 review 和后续系统优化。

---

## 25. 失败指纹

NightShift 应该通过以下信息识别低价值重复尝试：

- error fingerprint
- diff fingerprint
- tactic fingerprint

若多次尝试本质相同且没有带来有效进展：

- 停止重试
- 挂起 issue
- 交给人处理

---

## 26. 进展模型

NightShift 区分三类进展：

### 26.1 Acceptance Progress

- 必要验证全部通过
- 产生了保留 commit
- branch 或 PR 已具备 review 条件

### 26.2 Diagnostic Progress

- 建立了稳定复现
- 缩小了 blocker 范围
- 沉淀了有价值的结构化洞见

### 26.3 No Progress

- 重复相同失败
- 测试结果没有改进
- 没有新增有效诊断信息

通常只有 acceptance progress 才应保留代码作为 review 候选。

diagnostic progress 应主要保留状态和说明，而不一定保留代码。

---

## 27. PR 与 Review Handoff

对于已经通过 acceptance 的 issue，NightShift 应生成：

- branch 名称
- commit SHA 列表
- validation summary
- 简洁的变更说明
- retry history
- 已知风险
- 推荐 reviewer 背景信息
- 如接入平台，则可生成 PR draft body

NightShift 可以自动创建 PR，但 merge 必须继续由人控制。

---

## 28. 报告

NightShift 应在以下时机生成运行报告：

- 队列耗尽
- 总运行预算耗尽
- 收到 stop 命令
- 触发 failure circuit breaker

报告应包含：

- 运行时长
- 各类 issue 数量统计
- accepted issue 列表
- blocked issue 列表
- PR 链接（如存在）
- retry 与 failure 汇总
- 详细日志路径

早晨 review 时，建议按以下顺序展示：

1. 小而且验证完备的 diff
2. 低风险 accepted 输出
3. 有明确 next step 的 blocked issue
4. 高风险改动
5. 仅有诊断产出的结果

报告不是告警的替代物。报告服务于 review 与追踪，告警服务于运行时异常场景下的及时感知。

---

## 29. CLI 设计

NightShift 的 CLI 建议分三组。

### 29.1 准备阶段

- `nightshift split --requirement '...' --repo /path/to/repo`
- `nightshift split --file requirement.md --repo /path/to/repo`

### 29.2 队列与执行

- `nightshift queue status`
- `nightshift queue show <id>`
- `nightshift run --repo /path/to/repo`
- `nightshift run --repo /path/to/repo --daemon`
- `nightshift run-one <id> --repo /path/to/repo`
- `nightshift status`
- `nightshift stop`

### 29.3 报告

- `nightshift report`
- `nightshift report --run <run-id>`

---

## 30. 配置

每个仓库建议有一个 `nightshift.yaml` 配置文件。

建议配置块包括：

- `project`
  - repo path
  - main branch

- `runner`
  - default engine
  - engine fallback
  - issue timeout
  - total overnight timeout

- `validation`
  - lint command
  - typecheck command
  - build command
  - core regression commands

- `retry`
  - max retries
  - failure circuit breaker
  - retry strategy defaults

- `pr`
  - labels
  - reviewers
  - provider integration

- `report`
  - output directory
  - notification settings

### 30.1 告警语义

`notification_settings` 不能只是一个被动的传输配置字段，必须绑定明确的事件语义。

建议的 critical alert 事件：

- run 非预期中止
- global timeout 达到
- circuit breaker 触发
- 环境异常导致整个队列无法推进
- state store 损坏或恢复失败
- 多个 issue 连续发生 engine crash

建议的 warning 级事件：

- issue 被 blocked
- 单个 issue 重试耗尽
- engine fallback 被触发
- 检测到持续 flaky validation

操作规则：

- critical alert 应尽快通知
- warning alert 可以按用户偏好做批量汇总或延迟发送

---

## 31. 状态所有权

NightShift 是 run state 和 issue state 的唯一真实来源。

Execution engine 可以输出：

- execution summary
- changed files
- self-reported outcome
- proposed commit message

NightShift 负责写入：

- authoritative attempt result
- issue state
- run state
- acceptance / rejection 记录

这能保证即便引擎输出不稳定，内核仍然可靠。

---

## 32. 状态目录结构

建议目录结构如下：

```text
nightshift/
  config.yaml
  issues/
    123.yaml
    241.yaml
  engines/
    codex.md
    claude_code.md
nightshift-data/
  runs/
    2026-03-27/
      run-state.json
      report.md
      issues/
        123.json
        241.json
.nightshift/
  worktrees/
    issue-123/
    issue-241/
```

---

## 33. MVP 范围

V4 有意收缩了 MVP。

### 必需项

- issue contract schema
- queue 与 run control
- Codex CLI adapter
- Claude Code CLI adapter
- isolated branch / worktree 管理
- independent validation gate
- rejection 与 rollback
- reporting

### 可选项，但不是 MVP 必需

- remote issue sync
- remote PR sync
- dashboard
- 依赖感知调度
- 并行执行

这是对更早版本“第一期做太多模块”的修正。

---

## 34. 成功指标

建议的首批指标：

- 首次尝试成功率
- 在 retry budget 内的最终成功率
- 单个 issue 平均耗时
- 每晚产出的 review-ready 结果数
- 人工 review 接受率
- 人工干预率

这些指标应服务于产品迭代，而不是用来做表面数字。

---

## 35. V4.1 总结

NightShift V4.1 统一了：

- PRD 视角下的产品工作流
- harness / kernel 视角下的执行纪律

它的核心特征是：

- 白天由人准备并批准 automation-ready issues
- 夜间由 Codex CLI 或 Claude Code CLI 执行
- 由 NightShift 独立完成验证
- 使用 branch 与 worktree 隔离执行现场
- 将 rejection 与 rollback 作为一等系统能力
- 第二天由人 review 并决定 merge

相比 V4，V4.1 额外补齐了四个此前定义不够完整的结构性问题：

- engine adapter 的错误契约
- `blocked` 与 `deferred` 的状态语义
- requirement splitter 的 repo context 获取策略
- 无人值守夜间运行所需的告警语义

这是当前最实用的一版设计，因为它既：

- 能被讲清楚是一个什么产品
- 也能被严肃地实现成一个可靠系统
