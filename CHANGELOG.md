# Changelog

本项目所有显著变更都记录在此文件。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.3.0] - 2026-11-24

结论可信度修复版本：没有度量过的审计不再冒充「未亮旗」，退化阈值不再静默吞掉旗标，报告版本行回到唯一事实来源。

### Fixed

- `cli` / `report`：对齐后的决策日不足一个 `--window`（或全部决策日都缺 `t + lag` 观测）时，此前 `detect_divergence` 返回空列表，CLI 打印「未亮旗 / no flags fired — 未发现代理上行且结果下行的反相关窗口」并以退出码 `0` 结束——那正是文档里给 CI 门禁用、表示「审计完成、没亮旗」的码。现在这条路径在写叙事与报告之前就以双语 `错误 error:` 说明「无法度量」：报出对齐决策日数、覆盖率缺口、窗口与 lag，退出码 `2`。HTML 报告的零旗卡片不再刷成绿色（`class="n good"` → 中性），「一窗未扫」改成独立的琥珀色卡片，明确写出这不是「未发现背离」的结论。
- `divergence`：`--theta` / `--corr-threshold` 传入 `nan` / `inf` 时，此前只校验 `theta < 0`——而 `nan < 0` 为假，于是所有比较恒假、扫描静默归零，内置回放（正常亮一条旗）也会输出「亮旗 flags 0」并以 `0` 退出。现在非有限阈值按既有双语 `ValueError` 契约报错，CLI 以退出码 `2` 结束。输入层本来就拒绝非有限数字，这里补齐同一前置条件。
- `report`：报告的版本行改读 `proxydrift.__version__`，不再查 `importlib.metadata`。此前在源码树里运行（没有 dist 元数据）会整行丢掉版本，而环境里装着旧版 `proxydrift` 时报告会被盖上旧版本号——一份报告无法自证是哪个版本产出的。

### Added

- `tests/test_divergence.py`（3 项）、`tests/test_cli.py`（3 项）、`tests/test_version.py`（2 项）：无法度量 / 非有限阈值 / 报告版本行的回归测试，全套 50 → 58 项。

[0.3.0]: https://github.com/SuperMarioYL/proxydrift/releases/tag/v0.3.0

## [0.2.0] - 2026-10-21

崩溃路径修复版本：审计在两类异常响应/路径下不再裸崩，发布谱系回归 main。

### Fixed

- `llm_review`：GLM/DeepSeek 网关返回 200 但响应体不是合法 JSON（典型于代理/网关错误页）时，此前 `json.JSONDecodeError` 会直接炸穿整次审计；现在按既有契约降级为「叙事跳过」，统计审计独立成立。
- `cli`：`--report` 指向不可写路径（只读文件系统、父路径是文件、权限不足）时，此前以裸 OSError traceback 退出；现在与输入错误同一契约——双语错误信息、退出码 2。
- 发布谱系：v0.2.0 自 main HEAD 打标签（v0.1.0 标签之后落在 main 的站点提交一并纳入），七个版本面（VERSION、pyproject、`__version__`、CHANGELOG、双 README、uv.lock）全部锁定 0.2.0。

### Added

- `tests/test_llm_review.py`（9 项）与 `tests/test_cli.py`（5 项）：叙事降级契约、provider 选择、退出码契约与报告写入错误路径的回归测试；全套 36 → 50 项。

[0.2.0]: https://github.com/SuperMarioYL/proxydrift/releases/tag/v0.2.0

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
