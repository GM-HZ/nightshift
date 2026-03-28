# 增加中文 README 说明

## 背景

NightShift 目前已经有英文 README，但对中文使用者不够友好。
需要补充一份中文 README，并且让仓库首页能明确引导中文读者进入中文文档。

## 目标

补充一份结构清晰、可直接给中文工程师阅读的 `README.zh-CN.md`，并在根 `README.md` 里提供明显入口。

## 范围要求

- 允许修改：
  - `README.md`
  - `README.zh-CN.md`
- 不允许修改：
  - Python 源码
  - 测试逻辑
  - NightShift 运行时行为

## 详细说明要求

中文 README 至少应覆盖：

- NightShift 是什么
- 当前仓库已经实现到什么程度
- 当前主要 CLI 命令有哪些
- 当前 product workflow 到了哪一步
- 当前已知边界和未完成项
- 如何开始本地使用

## 验收要求

- 仓库根目录存在 `README.zh-CN.md`
- 根 `README.md` 顶部或显著位置有中文入口
- 中文 README 内容不是英文 README 的机械逐句翻译，而是适合中文读者快速理解当前仓库状态
- 文案应与当前实现状态一致，不能虚构未实现能力

## 验证建议

- 至少检查 `README.md` 中存在中文入口
- 至少检查 `README.zh-CN.md` 已创建且非空
- 如有必要，可用轻量命令验证文件存在和关键标题

## 风险和注意事项

- 不要把未来规划写成已实现能力
- 不要把 kernel 和 product workflow 混淆
- 保持中文表达自然，不要堆砌直译术语
