"""The ``proxydrift`` console command — audit, demo, --show-template.

One command per step of the happy path:

* ``proxydrift demo`` — replay the bundled synthetic creator-growth
  loop; no data, no API keys, one planted divergence flag;
* ``proxydrift --show-template`` — print the two-stream CSV contract;
* ``proxydrift audit proxy.csv outcome.csv --lag 7`` — audit your own
  streams: terminal summary, ``report.html``, optional GLM/DeepSeek
  narrative when a key is set.

Exit codes (documented for CI use):

* ``0`` — audit ran clean, no flag fired (``demo``: planted flag fired);
* ``1`` — audit ran clean, at least one divergence flag fired;
* ``2`` — usage or input error (bad CSV, bad parameters, broken demo).
"""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .align import AlignedStreams, DEFAULT_LAG_DAYS, align_streams
from .demo_data import (
    DEMO_SEED,
    DEMO_STORY,
    build_demo_replay,
)
from .divergence import (
    DEFAULT_CORR_THRESHOLD,
    DEFAULT_MAX_SUSPECTS,
    DEFAULT_THETA,
    DEFAULT_WINDOW,
    DivergenceFlag,
    detect_divergence,
)
from .llm_review import LLMReviewError, review_flags
from .report import (
    DEFAULT_OUTCOME_LABEL,
    DEFAULT_PROXY_LABEL,
    DEFAULT_REPORT_TITLE,
    print_terminal_summary,
    write_report,
)
from .streams import (
    OutcomeEvent,
    ProxyEvent,
    StreamValidationError,
    load_outcome_stream,
    load_proxy_stream,
)

EXIT_OK = 0
EXIT_FLAGGED = 1
EXIT_ERROR = 2

DEFAULT_REPORT = "report.html"


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"proxydrift {__version__}")
        return EXIT_OK
    if args.show_template:
        print(_template_text())
        return EXIT_OK
    if args.command == "audit":
        return _cmd_audit(args)
    if args.command == "demo":
        return _cmd_demo(args)
    parser.print_help()
    return EXIT_ERROR


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proxydrift",
        description=(
            "ProxyDrift — 把 Agent 决策流与延迟到达的真实结果流做 lag 对齐 join，"
            "在背离窗口亮旗 / the audit CLI that flags agents improving "
            "the proxy while real outcomes sink."
        ),
        epilog=(
            "退出码 exit codes: 0 未亮旗 no flags · 1 有旗标 flags fired · "
            "2 输入或参数错误 input/usage error"
        ),
    )
    parser.add_argument(
        "--version", action="store_true", help="打印版本并退出 / print version and exit"
    )
    parser.add_argument(
        "--show-template",
        action="store_true",
        help=(
            "打印两条输入 CSV 的契约模板并退出 / print the two-stream "
            "CSV input contract and exit"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="{audit,demo}")

    audit_parser = subparsers.add_parser(
        "audit",
        help="对你自己的两条数据流跑背离审计 / audit your own two streams",
        description=(
            "加载 proxy/outcome 两份 CSV，lag 对齐 join，窗口化背离检测，"
            "输出终端审计与 report.html。"
        ),
    )
    audit_parser.add_argument(
        "proxy_csv", help="代理流 proxy stream CSV（date, action_id, proxy_value）"
    )
    audit_parser.add_argument(
        "outcome_csv", help="结果流 outcome stream CSV（date, outcome_value）"
    )
    audit_parser.add_argument(
        "--proxy-label",
        default=DEFAULT_PROXY_LABEL,
        help="报告中代理流的名称 / label for the proxy stream in the report",
    )
    audit_parser.add_argument(
        "--outcome-label",
        default=DEFAULT_OUTCOME_LABEL,
        help="报告中结果流的名称 / label for the outcome stream",
    )
    _add_tuning_options(audit_parser)
    _add_report_options(audit_parser)

    demo_parser = subparsers.add_parser(
        "demo",
        help="重放内置合成创作者增长回放 / replay the bundled synthetic demo",
        description=(
            "无需数据、无需 key：重放内置的公众号内容 Agent 合成回放"
            "（确定性数据，seed 固定），一条背离旗标应声亮起。"
        ),
    )
    demo_parser.add_argument(
        "--seed",
        type=int,
        default=DEMO_SEED,
        help="合成回放的随机种子（默认固定值，输出可复现）/ replay seed",
    )
    _add_tuning_options(demo_parser)
    _add_report_options(demo_parser)

    return parser


def _add_tuning_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group(
        "检测阈值 detection thresholds"
    )
    group.add_argument(
        "--lag",
        type=int,
        default=DEFAULT_LAG_DAYS,
        help=f"结果流延迟天数（默认 {DEFAULT_LAG_DAYS}）/ outcome delay in days",
    )
    group.add_argument(
        "--window",
        type=int,
        default=DEFAULT_WINDOW,
        help=f"滚动窗口天数（默认 {DEFAULT_WINDOW}）/ rolling window in days",
    )
    group.add_argument(
        "--theta",
        type=float,
        default=DEFAULT_THETA,
        help=(
            f"趋势阈值 σ/天（默认 {DEFAULT_THETA}）：代理需 > +θ 且结果 < -θ "
            "/ trend threshold in sigma per day"
        ),
    )
    group.add_argument(
        "--corr-threshold",
        type=float,
        default=DEFAULT_CORR_THRESHOLD,
        help=(
            f"窗口相关系数上限（默认 {DEFAULT_CORR_THRESHOLD}）/"
            " max window correlation"
        ),
    )
    group.add_argument(
        "--max-suspects",
        type=int,
        default=DEFAULT_MAX_SUSPECTS,
        help=f"每条旗标列出的嫌疑动作数（默认 {DEFAULT_MAX_SUSPECTS}）/ suspects per flag",
    )


def _add_report_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("报告 report")
    group.add_argument(
        "--report",
        type=Path,
        default=Path(DEFAULT_REPORT),
        help=f"HTML 报告路径（默认 {DEFAULT_REPORT}）/ report path",
    )
    group.add_argument(
        "--no-report",
        action="store_true",
        help="只出终端审计，不写 HTML / skip the HTML report",
    )
    group.add_argument(
        "--no-llm",
        action="store_true",
        help="跳过审计叙事（即使设置了 API key）/ skip the model narrative",
    )
    group.add_argument(
        "--open",
        action="store_true",
        help="写完报告后在浏览器打开 / open the report in a browser",
    )
    group.add_argument(
        "--title",
        default=None,
        help="报告标题 / report title",
    )


def _cmd_audit(args: argparse.Namespace) -> int:
    try:
        proxy = load_proxy_stream(args.proxy_csv)
        outcome = load_outcome_stream(args.outcome_csv)
    except StreamValidationError as exc:
        print(f"错误 error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    flags = _run_flow(
        proxy,
        outcome,
        args,
        proxy_label=args.proxy_label,
        outcome_label=args.outcome_label,
    )
    return EXIT_FLAGGED if flags else EXIT_OK


def _cmd_demo(args: argparse.Namespace) -> int:
    replay = build_demo_replay(args.seed)
    print("ProxyDrift demo — 合成创作者增长回放 / synthetic creator-growth replay")
    print(f"  {DEMO_STORY}")
    print(
        f"  数据完全合成、确定性生成（seed = {args.seed}），仅用于演示检测机制"
        " / fully synthetic, deterministic, for demonstrating the mechanism only."
    )
    print()
    flags = _run_flow(
        replay.proxy_events,
        replay.outcome_events,
        args,
        proxy_label=replay.proxy_label,
        outcome_label=replay.outcome_label,
    )
    if not flags:
        print(
            "警告 warning: 内置回放未亮旗—— planted divergence not detected."
            " 这是回归，请到 GitHub Issues 报告 / please file an issue.",
            file=sys.stderr,
        )
        return EXIT_ERROR
    return EXIT_OK


def _run_flow(
    proxy: Sequence[ProxyEvent],
    outcome: Sequence[OutcomeEvent],
    args: argparse.Namespace,
    *,
    proxy_label: str,
    outcome_label: str,
) -> list[DivergenceFlag]:
    """Wire streams → align → divergence → narrative → report → terminal."""
    try:
        aligned: AlignedStreams = align_streams(proxy, outcome, lag_days=args.lag)
        flags = detect_divergence(
            aligned,
            window=args.window,
            theta=args.theta,
            corr_threshold=args.corr_threshold,
            max_suspects=args.max_suspects,
        )
    except ValueError as exc:
        print(f"错误 error: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_ERROR) from exc

    narrative = None
    narrative_source = None
    notes: list[str] = []
    if args.no_llm:
        notes.append(
            "审计叙事 narrative: skipped — --no-llm / disabled by --no-llm"
        )
    else:
        try:
            review = review_flags(aligned, flags)
        except LLMReviewError as exc:
            notes.append(f"审计叙事 narrative: skipped — {exc}")
        else:
            if review is None:
                notes.append(
                    "审计叙事 narrative: skipped — 未设置 ZHIPU_API_KEY / "
                    "DEEPSEEK_API_KEY，统计审计独立成立 / no API key set; "
                    "the statistical audit stands alone"
                )
            else:
                narrative = review.narrative
                narrative_source = review.source

    report_path = None
    if not args.no_report:
        # PingFang (the CJK chart font on macOS) has no true bold face;
        # matplotlib falls back to weight 600 and logs a notice about
        # it.  The fallback renders correctly, so keep the terminal
        # output clean for the audit itself.
        logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
        report_path = write_report(
            args.report,
            aligned,
            flags,
            title=args.title or DEFAULT_REPORT_TITLE,
            proxy_label=proxy_label,
            outcome_label=outcome_label,
            narrative=narrative,
            narrative_source=narrative_source,
            window=args.window,
        )

    print_terminal_summary(
        aligned, flags, window=args.window, report_path=report_path
    )
    for note in notes:
        print(note)
    if narrative_source is not None:
        print(f"审计叙事 narrative: {narrative_source}")
    if report_path is not None:
        print(f"HTML 报告 report: {report_path}")
        if args.open:
            webbrowser.open(report_path.resolve().as_uri())
    return flags


def _template_text() -> str:
    """The two-stream CSV contract, illustrated with real replay rows."""
    replay = build_demo_replay()
    proxy_rows = "\n".join(
        f"{event.t.isoformat()},{event.action_id},{event.proxy_value}"
        for event in replay.proxy_events[:3]
    )
    outcome_rows = "\n".join(
        f"{event.t.isoformat()},{event.outcome_value}"
        for event in replay.outcome_events[:3]
    )
    return f"""ProxyDrift 两流输入契约 / two-stream input contract

前置条件 precondition：需要同时拥有两条流——
  1) proxy   代理流：Agent 的决策日志（仪表盘/Agent 框架导出）
  2) outcome 结果流：延迟到达的真实业务指标（CRM/留存/转化报表）
没有可按日期 join 的结果流，就没有审计的 oracle——这是范围设计。

proxy.csv — Agent 决策流，每行动作一行 / one row per agent action
  date         YYYY-MM-DD 决策日 decision day
  action_id    动作/策略的稳定标识 stable action identifier
  proxy_value  该动作挣到的代理指标 the metric the agent was handed
----
date,action_id,proxy_value
{proxy_rows}
…

outcome.csv — 延迟真实结果流，每天一行 / one row per day
  date           YYYY-MM-DD 观测日 observation day
  outcome_value  当日真实结果 the delayed ground-truth metric
----
date,outcome_value
{outcome_rows}
…

对齐方式 alignment：决策日 t 的动作与 t + lag 天观测到的结果配对（--lag，默认 7）。
缺失观测的决策日会作为覆盖率缺口列出，绝不插值。

下一步 next：
  proxydrift audit proxy.csv outcome.csv --lag 7"""


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
