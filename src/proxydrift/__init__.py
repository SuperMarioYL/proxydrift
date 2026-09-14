"""ProxyDrift — the proxy–outcome divergence audit for goal-driven agents.

Point an agent at a measurable proxy and it will optimize that proxy.
The real outcome arrives days later, somewhere else — and nothing in
the eval loop ever compares the two.  ProxyDrift is the missing audit:
a lag-aware time join of the agent's decision stream against the
delayed ground-truth outcome stream, flagging windows where the proxy
climbs while the outcome sinks and the two anti-correlate.

Quick map of the package:

* :mod:`proxydrift.streams` — load and strictly validate the two CSVs;
* :mod:`proxydrift.align` — lag-shift the outcome and join on daily
  buckets, surfacing coverage gaps instead of interpolating;
* :mod:`proxydrift.divergence` — the pure windowed detection engine and
  the mandatory correlational verdict stamped on every flag;
* :mod:`proxydrift.report` — the terminal summary and the
  self-contained HTML report;
* :mod:`proxydrift.llm_review` — one optional GLM/DeepSeek call that
  narrates already-flagged windows (no key → skipped);
* :mod:`proxydrift.demo_data` — the bundled deterministic synthetic
  replay with planted divergence;
* :mod:`proxydrift.cli` — the ``proxydrift`` console command.
"""

from .align import (
    DEFAULT_LAG_DAYS,
    AlignedStreams,
    CoverageGap,
    DayPair,
    align_streams,
)
from .demo_data import DEMO_SEED, DemoReplay, build_demo_replay
from .divergence import (
    CORRELATIONAL_VERDICT,
    DEFAULT_WINDOW,
    DivergenceFlag,
    audit,
    detect_divergence,
)
from .llm_review import LLMReviewError, ReviewResult, review_flags
from .report import (
    build_report_html,
    format_terminal_summary,
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

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # streams
    "OutcomeEvent",
    "ProxyEvent",
    "StreamValidationError",
    "load_outcome_stream",
    "load_proxy_stream",
    # align
    "DEFAULT_LAG_DAYS",
    "AlignedStreams",
    "CoverageGap",
    "DayPair",
    "align_streams",
    # divergence
    "CORRELATIONAL_VERDICT",
    "DEFAULT_WINDOW",
    "DivergenceFlag",
    "audit",
    "detect_divergence",
    # report
    "build_report_html",
    "format_terminal_summary",
    "print_terminal_summary",
    "write_report",
    # llm review
    "LLMReviewError",
    "ReviewResult",
    "review_flags",
    # demo
    "DEMO_SEED",
    "DemoReplay",
    "build_demo_replay",
]
