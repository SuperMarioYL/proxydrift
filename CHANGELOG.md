# Changelog

本项目所有显著变更都记录在此文件。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-09-14

首个公开版本：两条流的代理指标背离审计，从引擎到报告到一条命令的演示。

### m1 — 两流对齐引擎（Added）

- `streams`：proxy/outcome 两份 CSV 的严格加载与校验，schema 错误双语（zh + en）报错，精确到文件、行、列。
- `align`：结果流按 `lag_days` 后移、按日聚合 join；缺失观测的决策日作为覆盖率缺口列出，绝不插值或前向填充。
- `divergence`：纯函数检测引擎——滚动窗口内代理 OLS 趋势 > +θ、lag 对齐结果趋势 < −θ、窗口 Pearson 相关 < −0.3 时亮旗；重叠/相邻旗标窗口合并；嫌疑动作按窗口内代理质量排序；每条旗标由代码强制标注 `correlational heuristic — not a causal verdict`。
- `tests/test_align.py`、`tests/test_divergence.py`：lag 方向、缺口处理、旗标谓词各臂、负控制、窗口合并、嫌疑排序、内置回放与示例数据的 33 项测试。

### m2 — 自包含审计报告（Added）

- `report`：双语终端审计摘要；单文件自包含 `report.html`——双趋势图（base64 内嵌 PNG）、旗标窗口底纹、嫌疑动作表、覆盖率缺口表、可选模型叙事块、托管版候补页脚。
- 每条旗标与叙事块均由代码盖章相关性判定标签，模型无权更改。

### m3 — 打磨与发布（Added）

- `cli`：`proxydrift audit`（对自有两流审计）、`proxydrift demo`（内置合成回放，无需数据与 key）、`--show-template`（两流输入契约）；退出码 0/1/2。
- `demo_data`：确定性合成创作者增长回放（公众号内容 Agent，单篇互动量 vs 7 日关注转化），内置植入背离，双写为 `examples/` 示例数据。
- `llm_review`：一次 OpenAI 兼容请求生成旗标窗口的中文审计叙事——GLM-4 系列（智谱开放平台，默认 `glm-4.6`）或 DeepSeek（`deepseek-flash` / `deepseek-v4-pro`）；无 key 优雅跳过，统计审计独立成立。
- 中英双语 README、MIT LICENSE、VERSION 与 pyproject 版本锁定测试（3 项，全套合计 36 项）、CI（lint + 测试矩阵）与 tag 触发的 release 工作流、真实演示 GIF。

[0.1.0]: https://github.com/SuperMarioYL/proxydrift/releases/tag/v0.1.0
