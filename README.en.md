**English** | [简体中文](./README.md)

<div align="center">

# ProxyDrift

**Your agent's proxy metric keeps climbing — the real business outcome is quietly getting worse.**

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&size=17&pause=1200&color=2563EB&center=true&vCenter=true&random=false&width=560&lines=proxy+%E2%86%91+interactions+climbing;outcome+%E2%86%93+7-day+conversion+sinking;lag+%3D+7d+before+truth+arrives;ProxyDrift+flags+the+divergence+window" alt="proxy ↑ interactions climbing; outcome ↓ 7-day conversion sinking; lag = 7d before truth arrives; ProxyDrift flags the divergence window" />

[![PyPI](https://img.shields.io/pypi/v/proxydrift.svg)](https://pypi.org/project/proxydrift/)
[![Python](https://img.shields.io/pypi/pyversions/proxydrift.svg)](https://pypi.org/project/proxydrift/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2563eb.svg)](./LICENSE)
[![CI](https://github.com/SuperMarioYL/proxydrift/actions/workflows/ci.yml/badge.svg)](https://github.com/SuperMarioYL/proxydrift/actions/workflows/ci.yml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/)

ProxyDrift runs a **lag-aware time join** between your agent's decision stream and the delayed ground-truth outcome stream, and flags the rolling windows where the proxy climbs, the outcome sinks, and the two anti-correlate — the failure class OpenAI monitors its internal coding agents for, built as one command any team can run on their own two data streams, with an optional audit narrative from GLM or DeepSeek.

[Quickstart](#quickstart) · [Demo](#demo) · [How it works](#how) · [Pricing](#pricing) · [Gitee mirror](https://gitee.com/SuperMarioYL/proxydrift)

</div>

<h2 id="why"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLXRyZW5kaW5nLWRvd24iCj4KICA8cGF0aCBzdHJva2U9Im5vbmUiIGQ9Ik0wIDBoMjR2MjRIMHoiIGZpbGw9Im5vbmUiLz4KICA8cGF0aCBkPSJNMyA3bDYgNmw0IC00bDggOCIgLz4KICA8cGF0aCBkPSJNMjEgMTBsMCA3bC03IDAiIC8+Cjwvc3ZnPg==" width="22" alt="" /> Why this exists</h2>

You point an agent at a business metric. The real outcome surfaces from CRM or retention reports 7 or 30 days later, so you hand the agent a measurable proxy — interactions, click-through, tickets closed. The agent optimizes exactly what it was handed: interactions climb, the dashboard goes green. The problem shows up elsewhere and later: the clicks came from shock titles and emoji bait, and the follow conversion that actually pays the bills is sinking.

The blind spot is structural: eval and observability dashboards score the same metric the agent was given, so **nothing in the loop ever compares proxy movement against downstream outcome movement**. By the time the numbers look wrong, the drift has compounded for weeks and all that's left is a manual deep-dive.

This is not hypothetical — OpenAI's [How we monitor internal coding agents for misalignment](https://openai.com/index/how-we-monitor-internal-coding-agents-misalignment/) confirms that reward hacking (proxy improving while the real outcome degrades) is a real, continuously monitored failure class for production agents. Their answer is an internal LLM review of trajectories that never leaves the building. ProxyDrift answers a different question: **"did the metric and the outcome diverge?"** — a two-stream time join, on your own data, in one command.

> <img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLWxvY2siCj4KICA8cGF0aCBzdHJva2U9Im5vbmUiIGQ9Ik0wIDBoMjR2MjRIMHoiIGZpbGw9Im5vbmUiLz4KICA8cGF0aCBkPSJNNSAxM2EyIDIgMCAwIDEgMiAtMmgxMGEyIDIgMCAwIDEgMiAydjZhMiAyIDAgMCAxIC0yIDJoLTEwYTIgMiAwIDAgMSAtMiAtMnYtNnoiIC8+CiAgPHBhdGggZD0iTTExIDE2YTEgMSAwIDEgMCAyIDBhMSAxIDAgMCAwIC0yIDAiIC8+CiAgPHBhdGggZD0iTTggMTF2LTRhNCA0IDAgMSAxIDggMHY0IiAvPgo8L3N2Zz4=" width="16" alt="" /> **Hard precondition**: ProxyDrift only accepts cases where you hold both streams — a proxy decision stream (exportable from agent logs or dashboards) and a **joinable delayed ground-truth outcome stream**. No outcome stream, no oracle; those teams self-select out — that's scope design, not a flaw. If you don't have your own data yet, the first command is `proxydrift demo`, on a bundled synthetic replay.

<h2 id="how"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLWdpdC1tZXJnZSIKPgogIDxwYXRoIHN0cm9rZT0ibm9uZSIgZD0iTTAgMGgyNHYyNEgweiIgZmlsbD0ibm9uZSIvPgogIDxwYXRoIGQ9Ik03IDE4bS0yIDBhMiAyIDAgMSAwIDQgMGEyIDIgMCAxIDAgLTQgMCIgLz4KICA8cGF0aCBkPSJNNyA2bS0yIDBhMiAyIDAgMSAwIDQgMGEyIDIgMCAxIDAgLTQgMCIgLz4KICA8cGF0aCBkPSJNMTcgMTJtLTIgMGEyIDIgMCAxIDAgNCAwYTIgMiAwIDEgMCAtNCAwIiAvPgogIDxwYXRoIGQ9Ik03IDhsMCA4IiAvPgogIDxwYXRoIGQ9Ik03IDhhNCA0IDAgMCAwIDQgNGg0IiAvPgo8L3N2Zz4=" width="22" alt="" /> How it works</h2>

The core primitive is the **proxy–outcome divergence audit**: bucket the agent decision stream per day, shift the outcome stream back by `lag_days`, join on daily buckets, then detect over rolling windows. A window flags when all three hold:

```
proxy_trend   > +θ      # the proxy climbs inside the window (σ/day, full-series normalized)
outcome_trend < −θ      # the lag-aligned outcome sinks inside it
corr          < −0.3    # the two move anti-correlated
```

```python
audit(proxy, outcome, lag_days=7, window=14) -> [DivergenceFlag]

DivergenceFlag {
  window: (t0, t1)             # flagged span (adjacent/overlapping windows merge)
  proxy_trend: float           # proxy slope inside the window (σ/day)
  outcome_trend: float         # lag-aligned outcome slope (σ/day)
  corr: float                  # Pearson correlation inside the window
  suspect_action_ids: [str]    # actions carrying the most proxy mass
  verdict: "correlational heuristic — not a causal verdict"   # stamped by code
}
```

Three design red lines:

- **Lag-aligned, never guessing time.** Decision days whose outcome observation is missing are listed as coverage gaps and dropped from the join — never interpolated or forward-filled; re-run once the data is backfilled.
- **Every flag is a correlational heuristic**, stamped by code, not by the LLM. A flag means "go review this window" — never proof of misbehavior, never a causal verdict.
- **The statistical audit stands alone.** With no API key set, the audit completes normally; the model only narrates windows the engine already flagged.

```
proxy.csv  ─┐
            ├─> streams.py ──> align.py ───> divergence.py ───> report.py ──> terminal + report.html
outcome.csv ─┘   (validate)    (lag-shift,     (windowed slopes,   (dual-trend chart, shaded windows,
                                 daily join)     corr, flags)        base64-embedded single-file HTML)
                                                      │
                                                      └──> llm_review.py (one GLM/DeepSeek call; no key → skip)

demo_data.py ──> bundled synthetic replay (planted divergence, deterministic, doubles as example + test fixture)
```

| Module | Responsibility |
| --- | --- |
| `streams.py` | Strict loading and validation of both CSVs; bilingual schema errors naming file, row, and column |
| `align.py` | Shift the outcome by `lag_days`, join on daily buckets; coverage gaps surfaced explicitly |
| `divergence.py` | Pure detection engine: windowed trends, correlation, merging, suspect ranking, verdict stamping |
| `report.py` | Bilingual terminal summary + self-contained HTML report (no external assets, renders offline) |
| `llm_review.py` | One OpenAI-compatible request for the Chinese audit narrative; skips gracefully without a key |
| `demo_data.py` | The deterministic synthetic creator-growth replay |

<h2 id="install"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLXBhY2thZ2UiCj4KICA8cGF0aCBzdHJva2U9Im5vbmUiIGQ9Ik0wIDBoMjR2MjRIMHoiIGZpbGw9Im5vbmUiLz4KICA8cGF0aCBkPSJNMTIgM2w4IDQuNWwwIDlsLTggNC41bC04IC00LjVsMCAtOWw4IC00LjUiIC8+CiAgPHBhdGggZD0iTTEyIDEybDggLTQuNSIgLz4KICA8cGF0aCBkPSJNMTIgMTJsMCA5IiAvPgogIDxwYXRoIGQ9Ik0xMiAxMmwtOCAtNC41IiAvPgogIDxwYXRoIGQ9Ik0xNiA1LjI1bC04IDQuNSIgLz4KPC9zdmc+" width="22" alt="" /> Install</h2>

```bash
# Option 1: don't install anything, just run it (try the demo first)
uvx proxydrift demo

# Option 2: pip
pip install proxydrift

# Option 3: from source
git clone https://github.com/SuperMarioYL/proxydrift.git
cd proxydrift
uv sync
uv run proxydrift demo
```

A [Gitee mirror](https://gitee.com/SuperMarioYL/proxydrift) is available for cloning from mainland China; the PyPI install is unaffected.

<h2 id="quickstart"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLXJvY2tldCIKPgogIDxwYXRoIHN0cm9rZT0ibm9uZSIgZD0iTTAgMGgyNHYyNEgweiIgZmlsbD0ibm9uZSIvPgogIDxwYXRoIGQ9Ik00IDEzYTggOCAwIDAgMSA3IDdhNiA2IDAgMCAwIDMgLTVhOSA5IDAgMCAwIDYgLThhMyAzIDAgMCAwIC0zIC0zYTkgOSAwIDAgMCAtOCA2YTYgNiAwIDAgMCAtNSAzIiAvPgogIDxwYXRoIGQ9Ik03IDE0YTYgNiAwIDAgMCAtMyA2YTYgNiAwIDAgMCA2IC0zIiAvPgogIDxwYXRoIGQ9Ik0xNSA5bS0xIDBhMSAxIDAgMSAwIDIgMGExIDEgMCAxIDAgLTIgMCIgLz4KPC9zdmc+" width="22" alt="" /> Quickstart</h2>

**Step 1 · see it work in 60 seconds** (no data, no keys):

```bash
uvx proxydrift demo
```

```text
ProxyDrift demo — 合成创作者增长回放 / synthetic creator-growth replay
  公众号内容 Agent 被交付「单篇互动量」作为优化目标；真实结果「7 日关注转化」要 7 天后才到达。
  Agent 逐渐把动作质量换成互动诱饵，代理指标一路上涨，延迟对齐后的转化率持续下沉。
  数据完全合成、确定性生成（seed = 20260914），仅用于演示检测机制 / fully synthetic, deterministic, for demonstrating the mechanism only.

ProxyDrift 背离审计 / divergence audit
  对齐 join        lag = 7 天/days, 已对齐决策日 joined decision days = 61
  覆盖缺口 gaps    2 天/days（结果流当日缺观测 / outcome not observed）
  扫描窗口 windows 48（window = 14 天/days）
  亮旗 flags       1

  FLAG 1  2026-07-07 → 2026-08-08（33 天/days）
    proxy 趋势 trend    +0.09 σ/day
    outcome 趋势 trend  -0.10 σ/day
    窗口相关 corr       -0.91
    嫌疑动作 suspects   title_shock, topic_pileup, emoji_bait
    判定 verdict        correlational heuristic — not a causal verdict（相关性启发式，非因果结论）
报告已写入 / report written: report.html
审计叙事 narrative: skipped — 未设置 ZHIPU_API_KEY / DEEPSEEK_API_KEY，统计审计独立成立 / no API key set; the statistical audit stands alone
HTML 报告 report: report.html
```

A self-contained `report.html` lands next to it: dual-trend chart (proxy climbing, lag-aligned outcome sinking), shaded flag windows, suspect-action table, coverage-gap table. Open it in a browser, or pass `--open` to launch it automatically.

**Step 2 · see what the input looks like**:

```bash
proxydrift --show-template
```

prints the two-CSV contract — `proxy.csv` (`date, action_id, proxy_value`, one row per agent action) exported from agent logs or the dashboard; `outcome.csv` (`date, outcome_value`, one row per day) exported from the delayed business metric.

**Step 3 · audit your own two streams**:

```bash
proxydrift audit proxy.csv outcome.csv --lag 7 \
  --proxy-label "per-article interactions" --outcome-label "7-day follow conversion"
```

The [`examples/`](./examples/) directory in this repo is the same replay written to disk — run it directly:

```bash
proxydrift audit examples/creator_growth_proxy.csv examples/creator_growth_outcome.csv --lag 7
```

(exit code 1 — a flag fired; see [CLI reference](#usage).)

**Optional · GLM/DeepSeek audit narrative**: set `ZHIPU_API_KEY` (GLM, default `glm-4.6`) or `DEEPSEEK_API_KEY` (default `deepseek-flash`) and re-run the audit; the report gains a model-written narrative block. Without a key, the statistical audit stands alone.

<h2 id="demo"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLXRlcm1pbmFsLTIiCj4KICA8cGF0aCBzdHJva2U9Im5vbmUiIGQ9Ik0wIDBoMjR2MjRIMHoiIGZpbGw9Im5vbmUiLz4KICA8cGF0aCBkPSJNOCA5bDMgM2wtMyAzIiAvPgogIDxwYXRoIGQ9Ik0xMyAxNWwzIDAiIC8+CiAgPHBhdGggZD0iTTMgNG0wIDJhMiAyIDAgMCAxIDIgLTJoMTRhMiAyIDAgMCAxIDIgMnYxMmEyIDIgMCAwIDEgLTIgMmgtMTRhMiAyIDAgMCAxIC0yIC0yeiIgLz4KPC9zdmc+" width="22" alt="" /> Demo</h2>

The full `proxydrift demo` run (terminal + `report.html`):

![ProxyDrift demo — terminal flag firing and report.html](./assets/proxydrift-demo.gif)

What happens in the replay: a synthetic WeChat Official Account content agent is handed per-article interactions. For three weeks it mostly writes deep originals while interactions decay naturally; then its action mix slides toward three engagement-bait actions — `title_shock`, `topic_pileup`, `emoji_bait` — and **interactions climb from a low of ~82 to 317 while the 7-day follow conversion drops from 5.4% to 2.2%**. The lag-aligned join puts both streams on one timeline, one flag lands on 2026-07-07 → 2026-08-08 (33 days, window correlation −0.91), and the suspects are exactly the three bait actions. All data is deterministic and synthetic (fixed seed), for demonstrating the detection mechanism only.

<h2 id="usage"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLWxpc3QtZGV0YWlscyIKPgogIDxwYXRoIHN0cm9rZT0ibm9uZSIgZD0iTTAgMGgyNHYyNEgweiIgZmlsbD0ibm9uZSIvPgogIDxwYXRoIGQ9Ik0xMyA1aDgiIC8+CiAgPHBhdGggZD0iTTEzIDloNSIgLz4KICA8cGF0aCBkPSJNMTMgMTVoOCIgLz4KICA8cGF0aCBkPSJNMTMgMTloNSIgLz4KICA8cGF0aCBkPSJNMyA0bTAgMWExIDEgMCAwIDEgMSAtMWg0YTEgMSAwIDAgMSAxIDF2NGExIDEgMCAwIDEgLTEgMWgtNGExIDEgMCAwIDEgLTEgLTF6IiAvPgogIDxwYXRoIGQ9Ik0zIDE0bTAgMWExIDEgMCAwIDEgMSAtMWg0YTEgMSAwIDAgMSAxIDF2NGExIDEgMCAwIDEgLTEgMWgtNGExIDEgMCAwIDEgLTEgLTF6IiAvPgo8L3N2Zz4=" width="22" alt="" /> CLI reference</h2>

```
proxydrift [--version] [--show-template] {audit,demo}
```

**`audit PROXY_CSV OUTCOME_CSV`** — run the divergence audit on your own two streams.

| Option | Default | Meaning |
| --- | --- | --- |
| `--lag` | `7` | outcome delay in days: decision day t pairs with the outcome observed at t+lag |
| `--window` | `14` | rolling window size (over joined decision days) |
| `--theta` | `0.05` | trend threshold (σ/day): proxy must exceed +θ, outcome −θ |
| `--corr-threshold` | `-0.3` | max window correlation |
| `--max-suspects` | `3` | suspect actions listed per flag |
| `--report PATH` | `report.html` | HTML report path |
| `--no-report` | — | terminal audit only, no HTML |
| `--no-llm` | — | skip the model narrative (even with a key set) |
| `--proxy-label` / `--outcome-label` | `proxy` / `outcome (lag-aligned)` | stream names shown in the report |
| `--title` | `ProxyDrift 背离审计报告` | report title |
| `--open` | — | open the report in a browser when written |

**`demo`** — replay the bundled synthetic loop, same options (plus `--seed`, fixed by default); the report automatically carries the replay's stream labels. A replay that fails to fire its planted flag is treated as a regression (exit code 2).

**Exit codes** (usable as a CI gate):

| Code | Meaning |
| --- | --- |
| `0` | audit completed, no flags (demo: planted flag fired as expected) |
| `1` | audit completed, at least one flag fired |
| `2` | input or usage error (schema mismatch, invalid thresholds, demo regression) |

<h2 id="config"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLWFkanVzdG1lbnRzIgo+CiAgPHBhdGggc3Ryb2tlPSJub25lIiBkPSJNMCAwaDI0djI0SDB6IiBmaWxsPSJub25lIi8+CiAgPHBhdGggZD0iTTQgMTBhMiAyIDAgMSAwIDQgMGEyIDIgMCAwIDAgLTQgMCIgLz4KICA8cGF0aCBkPSJNNiA0djQiIC8+CiAgPHBhdGggZD0iTTYgMTJ2OCIgLz4KICA8cGF0aCBkPSJNMTAgMTZhMiAyIDAgMSAwIDQgMGEyIDIgMCAwIDAgLTQgMCIgLz4KICA8cGF0aCBkPSJNMTIgNHYxMCIgLz4KICA8cGF0aCBkPSJNMTIgMTh2MiIgLz4KICA8cGF0aCBkPSJNMTYgN2EyIDIgMCAxIDAgNCAwYTIgMiAwIDAgMCAtNCAwIiAvPgogIDxwYXRoIGQ9Ik0xOCA0djEiIC8+CiAgPHBhdGggZD0iTTE4IDl2MTEiIC8+Cjwvc3ZnPg==" width="22" alt="" /> Configuration</h2>

Detection thresholds are CLI options (see the table above). The model narrative is configured through environment variables:

| Variable | Effect |
| --- | --- |
| `ZHIPU_API_KEY` | enable the GLM narrative (Zhipu open platform, primary; default model `glm-4.6`) |
| `DEEPSEEK_API_KEY` | enable the DeepSeek narrative (default `deepseek-flash`) |
| `PROXYDRIFT_LLM_PROVIDER` | force `glm` or `deepseek` (GLM wins when both keys are set) |
| `PROXYDRIFT_GLM_MODEL` | override the GLM model name (within the GLM-4 series) |
| `PROXYDRIFT_DEEPSEEK_MODEL` | override the DeepSeek model name (e.g. `deepseek-v4-pro`) |

The narrative is a single OpenAI-compatible `chat/completions` request with a 30-second timeout; a failed request is reported and skipped — **it never affects the audit itself**. The model only describes the statistical shape of already-flagged windows; the correlational verdict label is stamped by code.

<h2 id="compare"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLXNjYWxlIgo+CiAgPHBhdGggc3Ryb2tlPSJub25lIiBkPSJNMCAwaDI0djI0SDB6IiBmaWxsPSJub25lIi8+CiAgPHBhdGggZD0iTTcgMjBsMTAgMCIgLz4KICA8cGF0aCBkPSJNNiA2bDYgLTFsNiAxIiAvPgogIDxwYXRoIGQ9Ik0xMiAzbDAgMTciIC8+CiAgPHBhdGggZD0iTTkgMTJsLTMgLTZsLTMgNmEzIDMgMCAwIDAgNiAwIiAvPgogIDxwYXRoIGQ9Ik0yMSAxMmwtMyAtNmwtMyA2YTMgMyAwIDAgMCA2IDAiIC8+Cjwvc3ZnPg==" width="22" alt="" /> Scope and comparison</h2>

| Question | Who answers it |
| --- | --- |
| "Did the metric we handed the agent improve?" | eval / observability dashboards (already their job) |
| "Does this agent's behavior look misaligned?" | OpenAI-style LLM trajectory review (internal, not for sale) |
| **"Did the proxy diverge from the delayed outcome? Which window? Which actions?"** | **ProxyDrift** |

What v0.1 deliberately does not do:

- causal attribution — flags stay correlational heuristics, labeled by code;
- web UI, real-time streaming ingestion (OpenTelemetry, live agent hooks) — offline batch CSV only;
- eval-platform export adapters (Kiln, W&B, …) — held until a second practitioner demand signal;
- alert webhooks (Lark/DingTalk/Slack) and scheduled monitoring — reserved for the hosted tier;
- auto-remediation or reward re-tuning — an audit tool doesn't write prescriptions.

<h2 id="pricing"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLWNyZWRpdC1jYXJkIgo+CiAgPHBhdGggc3Ryb2tlPSJub25lIiBkPSJNMCAwaDI0djI0SDB6IiBmaWxsPSJub25lIi8+CiAgPHBhdGggZD0iTTMgNW0wIDNhMyAzIDAgMCAxIDMgLTNoMTJhMyAzIDAgMCAxIDMgM3Y4YTMgMyAwIDAgMSAtMyAzaC0xMmEzIDMgMCAwIDEgLTMgLTN6IiAvPgogIDxwYXRoIGQ9Ik0zIDEwbDE4IDAiIC8+CiAgPHBhdGggZD0iTTcgMTVsLjAxIDAiIC8+CiAgPHBhdGggZD0iTTExIDE1bDIgMCIgLz4KPC9zdmc+" width="22" alt="" /> Pricing</h2>

**The self-hosted CLI is free and MIT-licensed, forever** — the audit engine, the report, and the demo all run locally; your data never leaves your machine.

**Hosted tier (beta waitlist open)**, for growth teams that don't want to wire cron jobs themselves:

| | Free self-hosted CLI | Hosted (waitlist) |
| --- | --- | --- |
| Two-stream divergence audit | one manual command | runs on a schedule |
| Alerts | terminal + report.html | Lark / DingTalk / Slack webhooks |
| Report history | local files | archived in the cloud, replayable |
| Deployment | your machines | Aliyun, optional private deployment (data stays in your domain) |
| Price | ¥0 | **¥299/month per monitored loop** (unlimited seats); first 5 founding teams **¥199/month** |

To join the waitlist: open an issue titled with `hosted-beta` on [GitHub Issues](https://github.com/SuperMarioYL/proxydrift/issues) (the report.html footer links there too). We reach out within 24 hours and run *your own two CSVs live* on a 30-minute call — if a flag fires on your real data, the founding price is settled on the call (Alipay/WeChat QR; no billing infrastructure before 5 paying teams).

The honest part: hosted-tier development starts only after the second real practitioner report on own data. The waitlist itself is the demand signal — it's the only thing we charge for early.

<h2 id="roadmap"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLXJvdXRlIgo+CiAgPHBhdGggc3Ryb2tlPSJub25lIiBkPSJNMCAwaDI0djI0SDB6IiBmaWxsPSJub25lIi8+CiAgPHBhdGggZD0iTTMgMTlhMiAyIDAgMSAwIDQgMGEyIDIgMCAwIDAgLTQgMCIgLz4KICA8cGF0aCBkPSJNMTkgN2EyIDIgMCAxIDAgMCAtNGEyIDIgMCAwIDAgMCA0eiIgLz4KICA8cGF0aCBkPSJNMTEgMTloNS41YTMuNSAzLjUgMCAwIDAgMCAtN2gtOGEzLjUgMy41IDAgMCAxIDAgLTdoNC41IiAvPgo8L3N2Zz4=" width="22" alt="" /> Roadmap</h2>

**v0.1.0 (current)** shipped: the lag-aware two-stream join engine, windowed divergence detection, bilingual terminal audit, self-contained HTML report, GLM/DeepSeek audit narrative, bundled synthetic replay with 36 tests, CI and release workflows.

**Next: deliberately frozen until the second practitioner signal.** Until a real user runs an audit on their own two streams and reports back, no new features — that's the honest test of whether the demand is real. Once the signal lands, the priorities are:

- scheduled two-stream audits + Lark/DingTalk alerts (the hosted-tier core);
- the first eval-platform export adapter (candidate: Kiln export format);
- more scenario presets (support-ticket deflection vs delayed CSAT, e-commerce exposure vs repeat purchase).

**The best way to contribute**: [run it once on your own two streams](https://github.com/SuperMarioYL/proxydrift/issues) and report what fired (or didn't) in an issue — your report directly decides what this project does next, and whether it keeps doing it.

<h2 id="license"><img src="data:image/svg+xml;base64,PHN2ZwogIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICB3aWR0aD0iMjQiCiAgaGVpZ2h0PSIyNCIKICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgZmlsbD0ibm9uZSIKICBzdHJva2U9IiMyNTYzZWIiCiAgc3Ryb2tlLXdpZHRoPSIyIgogIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogIGNsYXNzPSJpY29uIGljb24tdGFibGVyIGljb25zLXRhYmxlci1vdXRsaW5lIGljb24tdGFibGVyLXNoaWVsZC1jaGVjayIKPgogIDxwYXRoIHN0cm9rZT0ibm9uZSIgZD0iTTAgMGgyNHYyNEgweiIgZmlsbD0ibm9uZSIvPgogIDxwYXRoIGQ9Ik0xMS40NiAyMC44NDZhMTIgMTIgMCAwIDEgLTcuOTYgLTE0Ljg0NmExMiAxMiAwIDAgMCA4LjUgLTNhMTIgMTIgMCAwIDAgOC41IDNhMTIgMTIgMCAwIDEgLS4wOSA3LjA2IiAvPgogIDxwYXRoIGQ9Ik0xNSAxOWwyIDJsNCAtNCIgLz4KPC9zdmc+" width="22" alt="" /> License</h2>

[MIT](./LICENSE) © 2026 SuperMarioYL. The demo data is deterministic and synthetic; it depicts no real account.

---

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>
