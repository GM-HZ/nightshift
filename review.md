明白，你要的不是“完整设计总表”，而是：

**相对你原始第一版设计，经过我们讨论后，需要新增 / 修改 / 强化的改动点清单**，并且按**重要优先级**整理，方便直接交给 Codex 去改设计文档和实现。

下面我按这个口径来整理。

---

# 相对第一版的设计改动清单

## P0：必须补上，不补就会影响 V1 可运行性

### 1. 把“验证闭环”从附属项升级为 Execution Issue 的准入条件

**第一版问题：**
原设计里已经有 Tier 1 / Tier 2 验证，但还没有明确写成：**没有可执行验证，就不能成为 execution issue**。

**需要改成：**

* execution issue 必须带有至少一种可执行验证方式：

  * issue-specific test
  * reproduction script
  * 可程序判定的 acceptance check
* 不满足这个条件的任务，降级为：

  * planning issue
  * repro issue
  * investigation issue

**建议写进设计的明确规则：**

> No executable validation, no execution issue.

**为什么这是 P0：**
没有这个，agent 无法判断“问题是否真的解决”，整个 loop 会失去闭环。

---

### 2. 明确“验证判定默认由程序完成，不由 agent 主观判断”

**第一版问题：**
第一版里有 test commands，但没有明确区分：

* 谁来判定通过
* 是 exit code / json / log pattern
* 还是让 agent 看结果自己解释

**需要改成：**

* 默认所有验证都由程序判定：

  * exit code
  * failing tests count
  * JSON 字段
  * 输出匹配
  * schema match
* agent 只能解释失败原因，不能作为最终“通过/解决”的裁判
* 只有极少数程序难以硬判定的场景，才允许 agent-as-judge，而且不能作为主门禁

**为什么这是 P0：**
否则系统会退化成“AI 说自己修好了”。

---

### 3. 给 issue model 新增 `verification contract`

**第一版问题：**
第一版只有：

* `issue_test_commands`
* `core_regression_commands`

但没有结构化定义“怎么判 pass”。

**需要改成：**
把验证从“命令列表”升级成“命令 + 判定方式”的合同，例如：

* reproduction / acceptance
* regression
* e2e（可选）

建议新增结构类似：

```yaml
verification:
  issue_validation:
    commands: [...]
    pass_condition: ...
  regression_validation:
    commands: [...]
    pass_condition: ...
  e2e_validation:
    required: false
    commands: [...]
    pass_condition: ...
```

**为什么这是 P0：**
不然 orchestrator 很难稳定实现统一验证逻辑。

---

### 4. 给每次 attempt 增加硬性“最小步长限制”

**第一版问题：**
第一版写了 “Plan a minimal attempt”，但这是软要求，不足以防止 agent 一次改太大。

**需要改成：**

* 在 `program.md` 里增加硬约束：

  * 每次 attempt 修改文件数不超过阈值
  * 新增代码不超过阈值
* 在 orchestrator 里增加检查：

  * `git diff --stat`
  * 超阈值直接拒绝进入测试
  * 分类为 `scope_expansion` 或 `attempt_rejected`

建议作为 issue 级可配置项：

```yaml
attempt_limits:
  max_files_changed: 3
  max_lines_added: 50
  max_lines_deleted: 30
```

**为什么这是 P0：**
否则“small-step progress”无法落地，reviewability 和 retry 也会失真。

---

### 5. 每个 attempt 必须有快照恢复点，失败后强制回滚

**第一版问题：**
第一版说“验证失败不保留”，但没有明确如何做到“失败现场彻底清理”。

**需要改成：**

* 每次 attempt 开始前记录：

  * `pre_edit_snapshot = git rev-parse HEAD`
* 验证失败后由 orchestrator 执行：

  * `git reset --hard <snapshot>`
  * `git clean -fd`（必要时白名单生成物）
* 不允许 agent 自己用自然语言式“我撤销一下”来清理现场

**为什么这是 P0：**
没有干净回滚，失败尝试会污染下一轮。

---

### 6. 增加 Pre-flight 预检阶段

**第一版问题：**
第一版默认直接进入 edit -> test，但没有确认当前分支 baseline 是否本来就是绿的。

**需要改成：**
在 edit 前加入 pre-flight：

* workspace clean check
* baseline Tier 1 / Tier 2 检查
* 必要服务 / 环境可用性检查

若 baseline 本身不过：

* 不进入 edit
* 直接标记：

  * `infra_blocked`
  * `dirty_baseline`
  * `flaky_baseline`

**为什么这是 P0：**
否则 agent 会把环境问题误判为代码问题。

---

### 7. 把“本地 state 是 source of truth”落实成 orchestrator 主写机制

**第一版问题：**
第一版强调 local structured state 很重要，但实现口径还偏概念化，没有明确谁维护 authoritative state。

**需要改成：**

* agent 只输出标准化结果
* orchestrator 校验后更新真正的：

  * run state
  * issue state
  * latest log
* 不把“真实状态”完全交给 agent 自己写

建议机制：

* agent 写 `attempt_result.json`
* orchestrator 根据 git/test 实际结果写 authoritative `issue_state.json`

**为什么这是 P0：**
否则状态可靠性不够，断点续跑也不稳。

---

### 8. 上下文架构要从“长上下文连续运行”改为“分层上下文 + 文件状态”

**第一版问题：**
第一版里默认的运行感觉更像单条连续上下文，但没有正式定义 context overflow 后怎么处理。

**需要改成：**

* issue context：只给当前 issue 所需的短上下文
* run context：由 orchestrator 持有全局进度摘要
* policy context：稳定规则写在 `program.md`
* continuity 依赖：

  * issue yaml
  * state json
  * run summary
  * compressed summaries

**建议明确写进原则：**

> Agent works in issue-scoped short context.
> Global continuity is maintained by orchestrator-managed local state.

**为什么这是 P0：**
不然长时间运行后，上下文必然失控。

---

## P1：强烈建议加入，会显著提高稳定性和吞吐

### 9. 为 bounded retries 增加“失败指纹机制”

**第一版问题：**
第一版有 retry 上限，但没有可靠机制判断“是不是在重复失败”。

**需要改成：**
对每次 attempt 记录并比较：

* 错误指纹
* diff 指纹
* hypothesis / tactic 指纹

若连续两次高度相似且没有进展：

* 直接挂起
* 分类为 `repeated_semantic_failure`

**为什么是 P1：**
没有这个也能跑，但会浪费很多夜间时间在伪尝试上。

---

### 10. 明确定义什么叫“progress”

**第一版问题：**
第一版里有“verified progress”，但没有把 progress 机械化。

**需要改成：**
定义 progress 例如包括：

* Tier 1 fail -> pass
* failing tests 数量下降
* deterministic repro 建立成功
* blocker 更清晰
* acceptance 更接近
* commit 产生
* 或知识性进展被结构化记录

同时区分：

* `commit-worthy progress`
* `state-worthy progress`

**为什么是 P1：**
这会直接影响 retry、suspend、summary 的准确性。

---

### 11. 把测试编辑权限从布尔值细化

**第一版问题：**
`can_edit_tests: true/false` 太粗。

**需要改成：**
细化为例如：

* `can_add_tests`
* `can_modify_existing_tests`
* `can_weaken_assertions`
* `requires_test_change_reason`

**为什么是 P1：**
可以更有效防止“通过改弱测试来作弊”。

---

### 12. 加入 workspace hygiene 规则

**第一版问题：**
第一版有 branch isolation，但没有把工作区卫生写成正式步骤。

**需要改成：**
在 issue/attempt 前后检查：

* working tree clean
* untracked file 控制
* build/temp/generated file 白名单
* service/resource cleanup

**为什么是 P1：**
长时间无人值守运行时，环境脏化是高频问题。

---

### 13. Blocked 状态细分为 blocker taxonomy

**第一版问题：**
blocked 太粗，不利于第二天接手。

**需要改成：**
至少细分：

* `infra_blocked`
* `scope_expansion`
* `repeated_semantic_failure`
* `dirty_baseline`
* `forbidden_path_required`
* `needs_human_decision`
* `flaky_validation`

**为什么是 P1：**
这会显著提升 morning review 的效率。

---

## P2：不是首要，但会让 V1 更顺滑

### 14. 增加 run-level 与 issue-level summary 压缩机制

**第一版问题：**
第一版有日志，但没有明确“超长历史如何压缩”。

**需要改成：**

* issue 只保留最近 attempts 细节 + 压缩摘要
* run 保留 scoreboard 风格摘要
* 原始长 history 可降级保存，不直接进入 prompt

**为什么是 P2：**
对长夜运行、断点恢复很有帮助，但不是最先卡住系统的点。

---

### 15. 增加 baseline drift 检测

**第一版问题：**
没有明确区分“这个 issue 导致失败”和“仓库/主干漂移导致 baseline 失绿”。

**需要改成：**
记录：

* last known green baseline
* baseline test fingerprint
* 当前 branch 与 base 的状态差异

若 baseline 漂移，则不让 agent盲修。

**为什么是 P2：**
非常有价值，但可在基础 loop 稳定后加入。

---

### 16. 增加 time budget，不只 attempt count budget

**第一版问题：**
第一版限制了 retry 次数，但没限制“某个 issue 吃掉整夜时间”。

**需要改成：**

* per-attempt max wall time
* per-issue per-night max wall time

**为什么是 P2：**
对整体吞吐优化很好，但不如验证、回滚、状态那样基础。

---

### 17. Morning review 从“列结果”升级为“排序交付”

**第一版问题：**
第一版提到了 summary 和 review order，但还不够明确。

**需要改成：**
按 review 优先级排序输出：

1. 小 diff + 全部验证通过
2. 低风险 + 可直接 review
3. blocker 清晰、适合人接手
4. 高风险 / 跨模块
5. 无 commit 但有有效分析

**为什么是 P2：**
更偏交付效率优化，不是底层生死点。

---

# 最适合直接交给 Codex 的一句话版本

你可以把下面这段直接交给 Codex，要求它基于第一版设计做 patch：

```text
请不要重写整个设计，只基于第一版做增量修改，重点补这几类缺口：

P0：
1. 明确 execution issue 的准入条件：没有可执行验证闭环的任务不能进入 execution queue。
2. 把验证判定明确为程序优先，不允许 agent 作为主裁判。
3. 为 issue model 增加 verification contract，定义 commands + pass_condition，而不只是 test command 列表。
4. 把 “plan a minimal attempt” 落地为硬约束：增加 attempt_limits，并要求 orchestrator 用 git diff --stat 做阈值检查。
5. 为每次 attempt 增加 pre-edit snapshot 和失败后的强制回滚机制。
6. 在 edit 前加入 pre-flight 阶段，确认 baseline 是绿的，否则标记为 infra/dirty baseline 类 blocker。
7. 把 local structured state 的设计落地为 orchestrator 主写 authoritative state，agent 只输出标准化结果文件。
8. 增加 context architecture：issue-scoped short context + orchestrator-managed run state，明确不能依赖单一长上下文连续运行。

P1：
9. 增加失败指纹机制，用于识别 repeated semantic failure。
10. 明确定义 progress，并区分 commit-worthy progress 与 state-worthy progress。
11. 将 can_edit_tests 细化为更小粒度权限。
12. 增加 workspace hygiene 规则。
13. 对 blocked 状态做 blocker taxonomy 细分。

P2：
14. 增加 summary 压缩机制，支持 context overflow 后恢复。
15. 增加 baseline drift 检测。
16. 增加 time budget。
17. 强化 morning review ordering 规则。

请输出：
- 相对第一版的修改说明
- 更新后的 design section 列表
- 需要新增/修改的 schema 字段
- 需要在 program.md 增加的规则
- 需要在 run_overnight.py 增加的 orchestrator 检查逻辑
```

---

如果你愿意，我下一条可以继续帮你把这份内容进一步压缩成**更像产品需求文档/工程任务单**的版本，变成 Codex 更容易直接执行的 TODO 格式。
