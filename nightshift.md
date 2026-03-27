# NightShift — 需求开发滚动执行工作流

核心 slogan：让需求开发像流水线一样滚动不停歇：人白天拆需求，NightShift 整晚自动执行、验证、推 PR，第二天早上人来 Review。

## 一、产品定位

NightShift 是一个轻量工作流外壳，不替代 Codex/Claude Code 的单任务执行能力，而是在外部做任务拆分 → 分发执行 → 外部验证 → 智能重试 → 提 PR 的滚动循环。

核心理念：
- 信任 Agent：Codex/Claude Code 已经能很好地完成单个 Issue，NightShift 只做编排和质量门禁
- 人机协作：人负责需求理解和拆分确认（高判断力），机器负责执行和验证（高重复性）
- 持续滚动：Issue 队列不断消费，一个做完做下一个，整晚不停歇

不做什么：
- 不做 Agent 平台，不重造 Codex/Claude Code
- 不做复杂的多 Agent 协作
- 不做 Issue 间的依赖管理（二期）
- 不做自动合并 PR（人工 Review 是底线）

## 二、整体架构

NightShift 分为两个阶段运行：

### 阶段一：需求准备（白天，人在场）
人输入大需求描述 → CLI 调用 AI 拆分成 Issue 列表（每个 Issue 带：描述、修改范围、测试用例、验收条件）→ 人工审核拆分结果（确认/调整/删除/补充）→ 确认后批量创建 Issue 进入待执行队列 → 启动 NightShift 执行循环

### 阶段二：自动执行（夜间，无人值守）
从队列取下一个 PENDING Issue → 创建独立 git 分支 → CLI 调用 Codex/Claude Code 执行 → Validation Gate（5 层验证）→ 通过则提 PR 做下一个 / 失败则智能降级重试（最多 3 次）→ 3 次仍失败标记人工介入做下一个 → 全部处理完生成运行报告

系统由 6 个模块组成：
- Requirement Splitter（需求拆分器）- 阶段一
- Issue Queue Manager（Issue 队列管理器）
- Task Runner（任务执行器，CLI 调用）
- Validation Gate（5 层验证门禁）
- Retry Controller（智能降级重试控制器）
- PR Dispatcher（PR 分发器）
- Report Generator（报告生成器）

## 三、模块详细设计

### 3.1 Requirement Splitter（需求拆分器）
职责：将一个大需求描述拆分成多个独立的、可单独实现的 Issue。
触发方式：CLI 命令 nightshift split --requirement '需求描述' --repo /path/to/repo
执行流程：
1. 读取仓库上下文（目录结构、关键文件、技术栈）
2. CLI 调用 AI 分析需求，输出拆分结果
3. 以结构化格式展示拆分结果，等待人工确认
4. 人工可以：确认、修改、删除某个 Issue、补充新 Issue
5. 确认后批量写入 Issue 队列

拆分原则（写入 AI prompt）：
- 每个 Issue 必须能独立实现和验证
- 每个 Issue 的修改范围尽量小且明确
- 每个 Issue 必须带有可执行的测试用例
- 每个 Issue 必须带有明确的验收条件
- Issue 之间不能有代码依赖

拆分输出示例（YAML 格式）：每个 issue 包含 title, description, scope（允许修改的文件列表）, testCases（每个含 description 和可选 command）, acceptanceCriteria

人工确认交互：展示所有 Issue 列表，用户输入 y/n/edit 确认

### 3.2 Issue Queue Manager（Issue 队列管理器）
职责：管理 Issue 的生命周期和状态流转。

Issue 状态机：PENDING → RUNNING → VALIDATING → PASSED → PR_OPENED，失败时 FAILED_RETRYABLE（回到 RUNNING，最多 3 次）→ FAILED_FINAL（需人工介入）

Issue 数据结构（TypeScript）：
- id: string（唯一标识）
- title: string（任务标题）
- description: string（详细描述）
- scope: string[]（允许修改的文件/目录范围）
- testCases: TestCase[]（Issue 自带的测试用例，每个含 description 和可选 command）
- acceptanceCriteria: string[]（验收条件）
- status: IssueStatus（当前状态）
- retryCount: number（已重试次数，最大 3）
- retryStrategy: string（当前重试策略描述）
- branch: string（工作分支名）
- lastError: string（最近一次失败原因）
- validationResult: ValidationResult（最近一次验证结果）
- prUrl: string（PR 链接）
- startedAt: string（开始执行时间）
- completedAt: string（完成时间）
- durationMs: number（耗时毫秒）

存储方式：MVP 阶段使用本地 JSON 文件存储，路径为 nightshift-data/issues.json。每次状态变更时原子写入。

CLI 命令：nightshift queue status / show / add / mark / clear

### 3.3 Task Runner（任务执行器）
职责：通过 CLI 调用 Codex/Claude Code 执行单个 Issue。
执行流程：
1. 从最新主分支创建独立工作分支：nightshift/issue-<id>-<short-title>
2. 组装 prompt（Issue 描述 + 仓库上下文 + 测试用例 + 验收条件）
3. CLI 调用 Codex/Claude Code，传入组装好的 prompt
4. 等待执行完成（受超时限制），收集 stdout/stderr 输出
5. 将结果传递给 Validation Gate

Prompt 组装模板包含：任务标题、详细描述、允许修改的文件范围、测试用例、验收条件、要求（只改 scope 内文件、确保测试通过、保持代码风格、补充单测、不引入 lint 错误）

分支管理策略：每个 Issue 独立分支，重试时 git reset --hard 回到初始状态重新执行，执行完成后自动 commit

超时控制：默认 30 分钟，超时强制终止，视为一次失败

### 3.4 Validation Gate（验证门禁）
职责：对执行结果进行 5 层外部验证。按顺序执行，任一层失败则整体失败。

第 1 层：测试验证 - 执行 project.testCommand，退出码为 0 则通过
第 2 层：静态检查 - 执行 lintCommand + typecheckCommand + buildCommand，全部退出码为 0 则通过，配置为空则跳过
第 3 层：Diff 范围审查 - git diff --name-only main...HEAD，检查修改文件是否在 issue.scope 范围内，新增测试文件例外
第 4 层：核心用例回归 - 执行 coreTestCommand，配置为空则跳过
第 5 层：Issue 测试用例验证 - 逐个验证 testCases，有 command 的直接执行，只有 description 的通过 AI 判断

ValidationResult 数据结构包含：passed, layers（每层的 passed/exitCode/output/skipped），failedAt, summary

### 3.5 Retry Controller（重试控制器）
职责：对验证失败的 Issue 进行智能降级重试。

三级降级策略：
- 第 1 次：原样重试 - 把错误日志和验证失败信息追加到 prompt，分支 reset 重新执行
- 第 2 次：缩小范围重试 - 从 acceptanceCriteria 中选出最核心的 1-2 条，缩小任务范围
- 第 3 次失败：标记人工介入 - 标记为 FAILED_FINAL，保留所有日志和 diff，跳到下一个 Issue

缩小范围的选择逻辑：
- 失败在第 1 层（测试）：保留所有验收条件，只追加错误信息
- 失败在第 3 层（diff 越界）：在 prompt 中强调 scope 限制
- 失败在第 5 层（Issue 测试用例）：只保留失败的测试用例对应的验收条件
- 其他情况：保留前 1-2 条验收条件

### 3.6 PR Dispatcher（PR 分发器）
职责：验证通过后自动提交代码并创建 PR。
执行流程：commit（message 格式 [NightShift] {title} (issue-{id})）→ push → 创建 PR（gh pr create 或 Aone CLI）→ 添加标签 nightshift-generated + needs-review → 自动分配 reviewer → 更新 Issue 状态为 PR_OPENED

PR 描述自动生成，包含：Issue 信息、修改文件列表、5 层验证结果、重试次数、执行耗时、执行引擎、人工 Review 提醒

### 3.7 Report Generator（报告生成器）
职责：每次运行结束后生成汇总报告。
触发时机：所有 Issue 处理完毕 / 运行超时被终止 / 触发连续失败熔断
报告内容：日期、运行时长、处理 Issue 数、总览（成功/失败/未处理数量）、成功 Issue 列表（含 PR 链接、重试次数、耗时）、失败 Issue 列表（含失败层、最后错误摘要）、详细日志路径

存储结构：nightshift-data/runs/<date>/report.md + issues-snapshot.json + logs/（每个 Issue 的 .log 和 -validation.json）

## 四、CLI 命令设计

阶段一：
- nightshift split --requirement '...' --repo /path/to/repo
- nightshift split --file requirement.md --repo /path/to/repo

Issue 管理：
- nightshift queue status / show <id> / add / mark <id> --status / clear

阶段二：
- nightshift run --repo /path/to/repo（前台）
- nightshift run --repo /path/to/repo --daemon（后台）
- nightshift run-one <id> --repo /path/to/repo（单个调试）
- nightshift status / stop

报告：
- nightshift report / nightshift report --run <run-id>

## 五、项目配置文件

每个目标仓库根目录放置 nightshift.yaml，包含：
- project: name, repo, mainBranch
- runner: engine (codex|claude-code), timeout (默认 1800s), maxTotalTime (默认 28800s)
- validation: testCommand, lintCommand, typecheckCommand, buildCommand, coreTestCommand
- retry: maxRetries (3), strategy (smart-degrade|fixed), consecutiveFailureLimit (5)
- pr: labels, autoAssign, reviewers
- report: outputDir, notify (dingtalk|feishu|空)

## 六、安全与保护机制

6.1 Git 安全：独立分支执行，绝不修改主分支；重试时 reset；通过 PR 流转；执行前检查工作区干净
6.2 执行保护：单 Issue 超时 30min；总运行 8h；连续 5 个 FAILED_FINAL 熔断；磁盘空间检查
6.3 Diff 保护：第 3 层审查 diff 范围，越界修改被拒绝（测试文件除外）
6.4 数据安全：原子写入 JSON；运行开始时创建快照；异常退出后可恢复

## 七、技术选型

- 语言：TypeScript (Node.js)
- CLI 框架：Commander.js
- 存储：本地 JSON 文件
- 执行器：Codex CLI / Claude Code CLI
- Git 操作：simple-git
- PR 创建：GitHub CLI (gh) / Aone CLI
- YAML 解析：js-yaml
- 日志：pino

## 八、MVP 范围与迭代计划

MVP（一期）：所有 7 个模块完整实现 + 项目配置文件

二期：Issue 间依赖管理、并行执行（git worktree）、Web Dashboard、通知集成、自动拆分质量评估、历史数据分析、CR 反馈闭环

## 九、成功指标

- 单 Issue 首次成功率 ≥ 50%
- 单 Issue 最终成功率 ≥ 70%（含重试）
- 单 Issue 平均耗时 ≤ 30 分钟
- 每晚处理 Issue 数 ≥ 10 个
- PR Review 通过率 ≥ 80%
- 人工干预率 ≤ 30%

## 十、典型使用场景

场景 1：大需求拆分执行 - 白天 split 拆分需求确认后，下班前 run --daemon 启动
场景 2：第二天早上 nightshift report 查看结果
场景 3：nightshift run-one 单个 Issue 调试
