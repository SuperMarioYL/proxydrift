"""Terminal summary and the self-contained HTML divergence report.

This module is the presentation half of the audit.  It consumes what
the engine already produced — the lag-aligned daily join
(:class:`~proxydrift.align.AlignedStreams`) plus the flags from
:func:`~proxydrift.divergence.detect_divergence` — and renders it two
ways:

* **terminal summary** — a bilingual (zh + en) audit block: joined
  days, coverage gaps, windows scanned, and each flag with its trends,
  correlation, suspect actions, and verdict;
* **report.html** — a single self-contained HTML file: inline CSS
  only, the matplotlib dual-trend chart (daily proxy vs lag-aligned
  outcome) embedded as a base64 PNG, shaded flag windows, a per-flag
  suspect-action breakdown, the coverage gaps the join dropped, an
  optional model narrative block, and the hosted-beta waitlist footer.

No engine logic lives here, and the HTML references no external
asset, CDN, or script — one file renders offline.  The verdict line
``correlational heuristic — not a causal verdict`` is stamped by this
module's code on every flag and on the narrative block; narrative
text, whatever model produced it, can never override the label.
"""

from __future__ import annotations

import base64
import io
from collections.abc import Sequence
from datetime import datetime, timedelta
from html import escape
from pathlib import Path

from .align import AlignedStreams
from .divergence import CORRELATIONAL_VERDICT, DEFAULT_WINDOW, DivergenceFlag

__all__ = [
    "DEFAULT_OUTCOME_LABEL",
    "DEFAULT_PROXY_LABEL",
    "DEFAULT_REPORT_TITLE",
    "ISSUES_URL",
    "REPO_URL",
    "VERDICT_ZH",
    "build_report_html",
    "format_terminal_summary",
    "print_terminal_summary",
    "windows_scanned",
    "write_report",
]

DEFAULT_PROXY_LABEL = "proxy"
DEFAULT_OUTCOME_LABEL = "outcome (lag-aligned)"
DEFAULT_REPORT_TITLE = "ProxyDrift 背离审计报告"

REPO_URL = "https://github.com/SuperMarioYL/proxydrift"
ISSUES_URL = REPO_URL + "/issues"

#: zh gloss of the code-stamped verdict; the label itself stays the exact
#: engine constant everywhere and is never translated or paraphrased.
VERDICT_ZH = "相关性启发式，非因果结论"

# Chart palette — the same hues the page CSS gives proxy/outcome, so the
# embedded PNG and the HTML read as one design.
_PROXY_COLOR = "#2563eb"
_OUTCOME_COLOR = "#dc2626"
_FLAG_BAND_COLOR = "#f59e0b"
_FLAG_LABEL_COLOR = "#b45309"
_GAP_COLOR = "#6b7280"


# ---------------------------------------------------------------------------
# terminal summary
# ---------------------------------------------------------------------------


def windows_scanned(aligned: AlignedStreams, window: int = DEFAULT_WINDOW) -> int:
    """Number of rolling windows the engine scans over the aligned join.

    Mirrors ``divergence.detect_divergence``: windows roll over joined
    days only, and a join shorter than ``window`` scans nothing.
    """
    return max(0, len(aligned.pairs) - window + 1)


def format_terminal_summary(
    aligned: AlignedStreams,
    flags: Sequence[DivergenceFlag],
    *,
    window: int = DEFAULT_WINDOW,
    report_path: str | Path | None = None,
) -> str:
    """Render the bilingual (zh + en) terminal audit block as a string.

    ``window`` is the rolling-window size the engine scanned with — only
    needed here to report how many windows were scanned.  When
    ``report_path`` is given, a final line points at the HTML report.
    """
    gap_note = (
        "（结果流当日缺观测 / outcome not observed）" if aligned.gaps else ""
    )
    lines = [
        "ProxyDrift 背离审计 / divergence audit",
        f"  对齐 join        lag = {aligned.lag_days} 天/days, "
        f"已对齐决策日 joined decision days = {len(aligned.pairs)}",
        f"  覆盖缺口 gaps    {len(aligned.gaps)} 天/days{gap_note}",
        f"  扫描窗口 windows {windows_scanned(aligned, window)}"
        f"（window = {window} 天/days）",
        f"  亮旗 flags       {len(flags)}",
    ]
    if flags:
        for index, flag in enumerate(flags, start=1):
            lines.extend(_terminal_flag_lines(index, flag))
    else:
        lines.append(
            "  未亮旗 / no flags fired — "
            "未发现代理上行且结果下行的反相关窗口"
        )
    if report_path is not None:
        lines.append(f"报告已写入 / report written: {report_path}")
    return "\n".join(lines)


def print_terminal_summary(
    aligned: AlignedStreams,
    flags: Sequence[DivergenceFlag],
    *,
    window: int = DEFAULT_WINDOW,
    report_path: str | Path | None = None,
) -> None:
    """Print the terminal audit block built by :func:`format_terminal_summary`."""
    print(
        format_terminal_summary(
            aligned, flags, window=window, report_path=report_path
        )
    )


def _terminal_flag_lines(index: int, flag: DivergenceFlag) -> list[str]:
    first_day, last_day = flag.window
    days = (last_day - first_day).days + 1
    suspects = (
        ", ".join(flag.suspect_action_ids)
        if flag.suspect_action_ids
        else "（无 / none）"
    )
    return [
        "",
        f"  FLAG {index}  {first_day.isoformat()} → {last_day.isoformat()}"
        f"（{days} 天/days）",
        f"    proxy 趋势 trend    {flag.proxy_trend:+.2f} σ/day",
        f"    outcome 趋势 trend  {flag.outcome_trend:+.2f} σ/day",
        f"    窗口相关 corr       {flag.corr:.2f}",
        f"    嫌疑动作 suspects   {suspects}",
        "    判定 verdict        "
        f"{CORRELATIONAL_VERDICT}（{VERDICT_ZH}）",
    ]


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------


def build_report_html(
    aligned: AlignedStreams,
    flags: Sequence[DivergenceFlag],
    *,
    title: str = DEFAULT_REPORT_TITLE,
    proxy_label: str = DEFAULT_PROXY_LABEL,
    outcome_label: str = DEFAULT_OUTCOME_LABEL,
    narrative: str | None = None,
    narrative_source: str | None = None,
    window: int = DEFAULT_WINDOW,
    generated_at: datetime | None = None,
) -> str:
    """Build the complete self-contained HTML report as a string.

    ``narrative`` is optional pre-generated audit narrative (the LLM
    review lives in ``llm_review``); it is escaped and rendered in its
    own block under ``narrative_source`` (a short model label such as
    ``GLM-4.6``).  The correlational verdict line inside that block is
    stamped here by code, not taken from the narrative.  ``generated_at``
    pins the timestamp for reproducible output (defaults to now, local
    timezone).
    """
    flags = list(flags)
    generated = (
        generated_at or datetime.now().astimezone()
    ).strftime("%Y-%m-%d %H:%M %Z")
    chart_b64 = _chart_png_base64(aligned, flags, proxy_label, outcome_label)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
{_CSS}
</style>
</head>
<body>
<main>
<header>
<h1><span class="px">Proxy</span><span class="ox">Drift</span></h1>
<p class="sub">背离审计报告 · divergence audit report</p>
<p class="meta">生成 generated {generated} · lag = {aligned.lag_days} 天/days · window = {window} 天/days · 代理流 proxy「{escape(proxy_label)}」· 结果流 outcome「{escape(outcome_label)}」</p>
</header>
<div class="stats">
{_stats_cards_html(aligned, flags, windows_scanned(aligned, window))}
</div>
<section class="notice">
<p><strong>判定声明 verdict —</strong> 所有旗标由代码强制标注为 <strong>{escape(CORRELATIONAL_VERDICT)}</strong>（{VERDICT_ZH}）。旗标指向「值得人工复核的窗口」，不是行为不当的证明，更不是因果结论。</p>
<p class="en-line">Every flag is stamped by code: <strong>{escape(CORRELATIONAL_VERDICT)}</strong>. A flag marks a window worth human review — never proof of misbehavior, never a causal claim.</p>
</section>
<section id="trend">
<h2>双趋势 <span class="en">dual trend</span></h2>
<img class="trend" alt="Dual-trend chart: daily proxy metric on the left axis against the lag-aligned outcome on the right axis, flagged windows shaded amber" src="data:image/png;base64,{chart_b64}">
<p class="caption">左轴 {escape(proxy_label)} 为决策日 t 的代理均值；右轴 {escape(outcome_label)} 取 t + {aligned.lag_days} 天观测到的真实结果（按 lag 对齐）。琥珀色底纹为亮旗窗口；灰色 ▼ 为结果流缺失、被剔除出 join 的决策日（不插值）。</p>
</section>
<section id="flags">
<h2>背离窗口 <span class="en">divergence windows</span></h2>
{_flags_body_html(aligned, flags)}
</section>
<section id="gaps">
<h2>覆盖率缺口 <span class="en">coverage gaps</span></h2>
{_gaps_body_html(aligned)}
</section>
{_narrative_html(narrative, narrative_source)}
<footer>
<p>托管版内测 hosted-beta waitlist：定时双流审计 + 飞书/钉钉告警 — 到 <a href="{ISSUES_URL}">GitHub Issues</a> 提交带「hosted-beta」的 issue。</p>
<p>{_version_line()}<a href="{REPO_URL}">github.com/SuperMarioYL/proxydrift</a> · MIT © 2026 SuperMarioYL</p>
</footer>
</main>
</body>
</html>
"""


def write_report(
    path: str | Path,
    aligned: AlignedStreams,
    flags: Sequence[DivergenceFlag],
    *,
    title: str = DEFAULT_REPORT_TITLE,
    proxy_label: str = DEFAULT_PROXY_LABEL,
    outcome_label: str = DEFAULT_OUTCOME_LABEL,
    narrative: str | None = None,
    narrative_source: str | None = None,
    window: int = DEFAULT_WINDOW,
    generated_at: datetime | None = None,
) -> Path:
    """Write the self-contained HTML report to ``path`` (UTF-8) and return it.

    Parent directories are created as needed; the file is written only
    after the report is fully built, so a failed render never leaves a
    partial report behind.
    """
    html_text = build_report_html(
        aligned,
        flags,
        title=title,
        proxy_label=proxy_label,
        outcome_label=outcome_label,
        narrative=narrative,
        narrative_source=narrative_source,
        window=window,
        generated_at=generated_at,
    )
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html_text, encoding="utf-8")
    return report_path


def _stats_cards_html(
    aligned: AlignedStreams, flags: Sequence[DivergenceFlag], scanned: int
) -> str:
    gap_count = len(aligned.gaps)
    flag_count = len(flags)
    cards = (
        (str(len(aligned.pairs)), "已对齐决策日 · joined decision days", ""),
        (f"{gap_count} 天/days", "覆盖率缺口 · coverage gaps", "bad" if gap_count else ""),
        (str(scanned), "扫描窗口 · windows scanned", ""),
        (str(flag_count), "亮旗 · flags", "bad" if flag_count else "good"),
    )
    return "\n".join(
        f'<div class="stat"><div class="n {cls}">{value}</div>'
        f'<div class="l">{label}</div></div>'
        for value, label, cls in cards
    )


def _flags_body_html(aligned: AlignedStreams, flags: Sequence[DivergenceFlag]) -> str:
    if not flags:
        return (
            '<article class="ok-card">\n<h3>未亮旗 / no flags fired</h3>\n'
            "<p>已扫描的滚动窗口里没有同时出现「代理上行 + 结果下行 + 反相关」。"
            "未亮旗不等于没有漂移——请复核结果流覆盖与阈值设置。</p>\n"
            '<p class="en-line">No scanned window combined a rising proxy, a sinking '
            "lag-aligned outcome, and anti-correlation. No flags is not proof of "
            "alignment — re-check outcome coverage and thresholds.</p>\n</article>"
        )
    return "\n".join(
        _flag_card_html(index, flag, aligned)
        for index, flag in enumerate(flags, start=1)
    )


def _flag_card_html(
    index: int, flag: DivergenceFlag, aligned: AlignedStreams
) -> str:
    first_day, last_day = flag.window
    days = (last_day - first_day).days + 1
    if flag.suspect_action_ids:
        rows = "".join(
            _suspect_row_html(*row) for row in _suspect_rows(aligned, flag)
        )
        suspect_table = (
            "<table>\n"
            "<thead><tr><th>嫌疑动作 suspect action</th>"
            '<th class="num">次数 count</th>'
            '<th class="num">proxy 质量 mass</th>'
            "<th>占比 share</th></tr></thead>\n"
            f"<tbody>\n{rows}\n</tbody>\n</table>"
        )
    else:
        suspect_table = ""
    return (
        '<article class="flag">\n'
        f"<h3>背离窗口 flag #{index} · <code>{first_day.isoformat()}</code>"
        f" → <code>{last_day.isoformat()}</code>"
        f' <span class="src">{days} 天/days</span></h3>\n'
        '<div class="flagstats">\n'
        '<div class="kv"><span class="k">proxy 趋势 trend · σ/day</span>'
        f'<span class="v proxy">{flag.proxy_trend:+.2f}</span></div>\n'
        '<div class="kv"><span class="k">outcome 趋势 trend · σ/day</span>'
        f'<span class="v outcome">{flag.outcome_trend:+.2f}</span></div>\n'
        '<div class="kv"><span class="k">窗口相关 corr</span>'
        f'<span class="v">{flag.corr:.2f}</span></div>\n'
        "</div>\n"
        f"{suspect_table}\n"
        '<p class="verdict">判定 verdict: '
        f"<strong>{escape(CORRELATIONAL_VERDICT)}</strong>（{VERDICT_ZH}）"
        "—— 由代码强制盖章，模型无权更改 / stamped by code, never by the model."
        "</p>\n</article>"
    )


def _suspect_rows(
    aligned: AlignedStreams, flag: DivergenceFlag
) -> list[tuple[str, int | None, float | None, float]]:
    """Per-suspect usage inside the flag window, read off the aligned join.

    The ranking itself stays owned by ``divergence``; this only presents
    each ranked suspect's count and share of the window's total proxy
    mass.  A suspect absent from the join (a flag not built from
    ``aligned``) degrades to ``None`` stats.
    """
    first_day, last_day = flag.window
    counts: dict[str, int] = {}
    masses: dict[str, float] = {}
    total_mass = 0.0
    for pair in aligned.pairs:
        if first_day <= pair.t <= last_day:
            for stat in pair.action_stats:
                counts[stat.action_id] = counts.get(stat.action_id, 0) + stat.count
                masses[stat.action_id] = (
                    masses.get(stat.action_id, 0.0) + stat.proxy_sum
                )
                total_mass += stat.proxy_sum
    rows: list[tuple[str, int | None, float | None, float]] = []
    for action_id in flag.suspect_action_ids:
        mass = masses.get(action_id)
        if mass is None:
            rows.append((action_id, None, None, 0.0))
        else:
            share = mass / total_mass if total_mass > 0 else 0.0
            rows.append((action_id, counts[action_id], mass, share))
    return rows


def _suspect_row_html(
    action_id: str, count: int | None, mass: float | None, share: float
) -> str:
    if count is None or mass is None:
        numeric_cells = '<td class="num">—</td><td class="num">—</td>'
        share_cell = "<td>—</td>"
    else:
        numeric_cells = (
            f'<td class="num">{count}</td><td class="num">{mass:,.1f}</td>'
        )
        width = min(100.0, max(share * 100.0, 2.0))
        share_cell = (
            '<td><div class="share"><div class="bar">'
            f'<span style="width:{width:.0f}%"></span></div>'
            f'<span class="pct">{share * 100:.0f}%</span></div></td>'
        )
    return (
        f"<tr><td><code>{escape(action_id)}</code></td>"
        f"{numeric_cells}{share_cell}</tr>"
    )


def _gaps_body_html(aligned: AlignedStreams) -> str:
    if not aligned.gaps:
        return (
            '<p class="caption">无覆盖率缺口——每个决策日都找到了 t + lag 的结果观测。'
            "/ No coverage gaps — every decision day found its lag-shifted "
            "outcome.</p>"
        )
    rows = "\n".join(
        f"<tr><td><code>{gap.t.isoformat()}</code></td>"
        f"<td><code>{gap.missing_outcome_date.isoformat()}</code></td></tr>"
        for gap in aligned.gaps
    )
    return (
        "<table>\n<thead><tr><th>决策日 decision day</th>"
        "<th>缺失的结果日 missing outcome（t + lag）</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>\n"
        '<p class="caption">这些决策日已从对齐 join 中剔除——不做插值或前向填充；'
        "补齐结果流后重跑即可纳入。/ Dropped from the join — never interpolated "
        "or forward-filled.</p>"
    )


def _narrative_html(narrative: str | None, source: str | None) -> str:
    if narrative is None or not narrative.strip():
        return ""
    paragraphs = "\n".join(
        f"<p>{escape(chunk.strip())}</p>"
        for chunk in narrative.strip().split("\n\n")
        if chunk.strip()
    )
    source_html = f' <span class="src">· {escape(source)}</span>' if source else ""
    return (
        '<aside class="narrative">\n'
        f"<h2>审计叙事 <span class=\"en\">audit narrative</span>{source_html}</h2>\n"
        f"{paragraphs}\n"
        '<p class="verdict">叙述由模型生成、仅描述已亮旗窗口的统计形状；判定标签由代码强制盖章：'
        f"<strong>{escape(CORRELATIONAL_VERDICT)}</strong>（{VERDICT_ZH}）。"
        "/ Narrative is model-generated description; the verdict label is "
        "stamped by code.</p>\n</aside>"
    )


def _version_line() -> str:
    """Installed distribution version prefix, or '' when running from a tree."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return f"ProxyDrift v{version('proxydrift')} · "
    except PackageNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# chart
# ---------------------------------------------------------------------------


#: Candidate CJK fonts, best-first per platform (macOS / Windows / Linux).
_CJK_FONT_CANDIDATES = (
    "PingFang SC",
    "Hiragino Sans GB",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
)


def _chart_font_families(proxy_label: str, outcome_label: str) -> list[str]:
    """Font family list for the chart, CJK-capable first when needed.

    matplotlib's per-glyph fallback never reaches past the first family
    that resolves, so DejaVu-first leaves CJK label text as empty boxes.
    When the stream labels carry characters beyond the Latin/Greek/
    Cyrillic range, the first installed CJK font is moved to the head —
    those fonts cover Latin as well, so ASCII text still renders.
    """
    from matplotlib import font_manager

    if not any(ord(ch) > 0x2E7F for ch in f"{proxy_label} {outcome_label}"):
        return ["DejaVu Sans"]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for name in _CJK_FONT_CANDIDATES:
        if name in available:
            return [name, "DejaVu Sans"]
    return ["DejaVu Sans"]


def _chart_png_base64(
    aligned: AlignedStreams,
    flags: Sequence[DivergenceFlag],
    proxy_label: str,
    outcome_label: str,
) -> str:
    """Render the dual-trend chart and return it as a base64-encoded PNG.

    Matplotlib is imported lazily so a terminal-only audit never pays for
    it, and ``Agg`` is forced because this renderer is headless by
    definition.  Default chart text stays ASCII (matplotlib's bundled
    DejaVu Sans carries no CJK glyphs); when the caller passes CJK
    stream labels, the first installed CJK font is moved to the head of
    the family list so those glyphs actually render.
    """
    import matplotlib

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    families = _chart_font_families(proxy_label, outcome_label)

    with plt.rc_context({"font.family": "sans-serif", "font.sans-serif": families}):
        fig, ax_proxy = plt.subplots(figsize=(10.0, 4.6))
        pairs = aligned.pairs
        if pairs:
            days = [pair.t for pair in pairs]
            ax_proxy.plot(
                days,
                [pair.proxy_value for pair in pairs],
                color=_PROXY_COLOR,
                linewidth=1.8,
                marker="o",
                markersize=3.0,
                label=f"{proxy_label} (left axis)",
            )
            ax_outcome = ax_proxy.twinx()
            ax_outcome.plot(
                days,
                [pair.outcome_value for pair in pairs],
                color=_OUTCOME_COLOR,
                linewidth=1.8,
                marker="s",
                markersize=3.0,
                label=f"{outcome_label} (right axis)",
            )
            for index, flag in enumerate(flags, start=1):
                first_day, last_day = flag.window
                ax_proxy.axvspan(
                    first_day,
                    last_day + timedelta(days=1),
                    color=_FLAG_BAND_COLOR,
                    alpha=0.16,
                    zorder=0,
                    label="flagged window" if index == 1 else None,
                )
                center = first_day + timedelta(
                    days=(last_day - first_day).days / 2 + 0.5
                )
                ax_proxy.text(
                    center,
                    0.97,
                    f"flag {index}",
                    transform=ax_proxy.get_xaxis_transform(),
                    ha="center",
                    va="top",
                    fontsize=8,
                    fontweight="bold",
                    color=_FLAG_LABEL_COLOR,
                )
            if aligned.gaps:
                gap_days = [gap.t for gap in aligned.gaps]
                ax_proxy.plot(
                    gap_days,
                    [0.04] * len(gap_days),
                    linestyle="none",
                    marker="v",
                    markersize=4.0,
                    color=_GAP_COLOR,
                    clip_on=False,
                    transform=ax_proxy.get_xaxis_transform(),
                    label="coverage gap (outcome missing)",
                )
            _style_chart_axes(ax_proxy, ax_outcome, aligned.lag_days)
            handles, labels = ax_proxy.get_legend_handles_labels()
            twin_handles, twin_labels = ax_outcome.get_legend_handles_labels()
            ax_proxy.legend(
                handles + twin_handles,
                labels + twin_labels,
                loc="upper left",
                fontsize=8,
                frameon=False,
            )
        else:
            ax_proxy.set_axis_off()
            ax_proxy.text(
                0.5,
                0.5,
                "no joined decision days — see coverage gaps below",
                transform=ax_proxy.transAxes,
                ha="center",
                va="center",
                color=_GAP_COLOR,
            )

        buffer = io.BytesIO()
        fig.savefig(
            buffer, format="png", dpi=150, bbox_inches="tight", facecolor="white"
        )
        plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _style_chart_axes(ax_proxy, ax_outcome, lag_days: int) -> None:
    """Axis labels, colors, and date ticks for the dual-trend chart."""
    from matplotlib import dates as mdates

    ax_proxy.set_title(
        "proxy vs lag-aligned outcome (daily)", fontsize=11, color="#374151", pad=12
    )
    ax_proxy.set_xlabel(
        f"decision day t (outcome observed at t + {lag_days} d)", fontsize=9
    )
    ax_proxy.set_ylabel("proxy", fontsize=9, color=_PROXY_COLOR)
    ax_outcome.set_ylabel("outcome (lag-aligned)", fontsize=9, color=_OUTCOME_COLOR)
    ax_proxy.tick_params(axis="x", labelsize=8)
    ax_proxy.tick_params(axis="y", labelsize=8, labelcolor=_PROXY_COLOR)
    ax_outcome.tick_params(axis="y", labelsize=8, labelcolor=_OUTCOME_COLOR)
    ax_proxy.spines["top"].set_visible(False)
    ax_outcome.spines["top"].set_visible(False)
    ax_proxy.spines["left"].set_color(_PROXY_COLOR)
    ax_outcome.spines["right"].set_color(_OUTCOME_COLOR)
    ax_proxy.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    ax_proxy.set_axisbelow(True)
    locator = mdates.AutoDateLocator()
    ax_proxy.xaxis.set_major_locator(locator)
    ax_proxy.xaxis.set_major_formatter(mdates.AutoDateFormatter(locator))


_CSS = """
html { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #f5f6f8;
  color: #111827;
  font: 15px/1.7 system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
}
main { max-width: 960px; margin: 0 auto; padding: 36px 20px 40px; }
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
code {
  font: 12.5px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #f3f4f6;
  border-radius: 4px;
  padding: 1px 5px;
}
h1 { margin: 0; font-size: 30px; letter-spacing: -0.5px; }
h1 .px { color: #2563eb; }
h1 .ox { color: #dc2626; }
.sub { margin: 2px 0 0; color: #4b5563; font-size: 15px; }
.meta { margin: 10px 0 0; color: #6b7280; font-size: 12.5px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 22px; }
.stat { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px 16px; }
.stat .n { font-size: 25px; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat .n.bad { color: #dc2626; }
.stat .n.good { color: #059669; }
.stat .l { margin-top: 2px; color: #6b7280; font-size: 12px; }
section, aside { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px 22px; margin-top: 20px; }
h2 { margin: 0 0 12px; font-size: 17px; }
h2 .en, .src, .en-line { color: #6b7280; font-weight: 500; }
h2 .en, .src { font-size: 12.5px; margin-left: 8px; }
.en-line { font-size: 13px; margin: 6px 0 0; }
.notice { background: #fffbeb; border-color: #f59e0b; }
.notice p { margin: 6px 0; }
img.trend { display: block; width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 6px; }
.caption { margin: 12px 0 0; color: #6b7280; font-size: 12.5px; }
article.flag, article.ok-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px 18px; }
article.flag { border-left: 4px solid #f59e0b; }
article.flag + article.flag { margin-top: 14px; }
article h3 { margin: 0 0 12px; font-size: 15px; }
article.ok-card h3 { color: #047857; }
.flagstats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
.kv .k { display: block; color: #6b7280; font-size: 12px; }
.kv .v { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
.kv .v.proxy { color: #2563eb; }
.kv .v.outcome { color: #dc2626; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th { text-align: left; color: #6b7280; font-weight: 600; font-size: 12px; border-bottom: 1px solid #e5e7eb; padding: 6px 8px; }
td { border-bottom: 1px solid #f3f4f6; padding: 7px 8px; vertical-align: middle; }
th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
.share { display: flex; align-items: center; gap: 8px; }
.bar { flex: none; width: 150px; height: 8px; border-radius: 4px; background: #eef2f7; overflow: hidden; }
.bar span { display: block; height: 100%; border-radius: 4px; background: #2563eb; }
.pct { color: #6b7280; font-size: 12px; font-variant-numeric: tabular-nums; }
.verdict { margin: 14px 0 0; padding: 8px 12px; border: 1px dashed #f59e0b; border-radius: 6px; background: #fffbeb; color: #92400e; font-size: 12.5px; }
aside.narrative { background: #f0f7ff; border-color: #bfdbfe; }
aside.narrative p { margin: 8px 0; }
footer { margin-top: 26px; text-align: center; color: #6b7280; font-size: 12.5px; }
footer p { margin: 4px 0; }
@media (max-width: 640px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
  .flagstats { grid-template-columns: 1fr; }
  .bar { width: 90px; }
}
@media print {
  body { background: #fff; }
  article.flag, aside.narrative { break-inside: avoid; }
}
""".strip()
