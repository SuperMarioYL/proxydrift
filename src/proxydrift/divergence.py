"""Windowed divergence detection over the lag-aligned two-stream join.

Pure functions, no I/O — everything here consumes the event and
alignment structures from ``streams`` and ``align``.

A rolling window of ``window`` aligned days flags when all three hold:

* ``proxy_trend   > +theta`` — the proxy climbs inside the window
* ``outcome_trend < -theta`` — the lag-aligned outcome sinks inside it
* ``corr          <  corr_threshold`` (default -0.3) — the two move
  anti-correlated

Trends are OLS slopes (value per calendar day) normalized by the full
aligned series' standard deviation, so a single scale-free ``theta``
serves streams measured in different units (e.g. 互动量 vs 转化率).
``corr`` is the Pearson correlation between the window's daily proxy
and lag-aligned outcome values.  Overlapping or directly adjacent
flagged windows merge into one flag whose statistics describe the merged
span; ``suspect_action_ids`` ranks the actions carrying the most proxy
mass inside that span.  Windows roll over aligned days (joined pairs),
not calendar days — coverage gaps are already excluded from the join and
are never interpolated.

Every flag carries the mandatory verdict stamped by this module — a
correlational heuristic, never a causal verdict.  No caller (and no
LLM) may alter it.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .align import DEFAULT_LAG_DAYS, AlignedStreams, DayPair, align_streams
from .streams import OutcomeEvent, ProxyEvent

__all__ = [
    "CORRELATIONAL_VERDICT",
    "DEFAULT_WINDOW",
    "DEFAULT_THETA",
    "DEFAULT_CORR_THRESHOLD",
    "DEFAULT_MAX_SUSPECTS",
    "DivergenceFlag",
    "audit",
    "detect_divergence",
]

#: Mandatory verdict stamped by code on every flag — correlational, never causal.
CORRELATIONAL_VERDICT = "correlational heuristic — not a causal verdict"

DEFAULT_WINDOW = 14
DEFAULT_THETA = 0.05
DEFAULT_CORR_THRESHOLD = -0.3
DEFAULT_MAX_SUSPECTS = 3


@dataclass(frozen=True)
class DivergenceFlag:
    """One flagged window of the proxy-outcome divergence audit."""

    window: tuple[date, date]  # (first decision day, last decision day) of the flagged span
    proxy_trend: float  # sigma-normalized proxy slope per day inside the window
    outcome_trend: float  # sigma-normalized lag-aligned outcome slope per day
    corr: float  # Pearson corr between proxy and lag-aligned outcome in the window
    suspect_action_ids: tuple[str, ...]  # actions carrying the most proxy mass
    verdict: str = CORRELATIONAL_VERDICT  # mandatory, stamped by code — never causal


def audit(
    proxy: Sequence[ProxyEvent],
    outcome: Sequence[OutcomeEvent],
    lag_days: int = DEFAULT_LAG_DAYS,
    window: int = DEFAULT_WINDOW,
    theta: float = DEFAULT_THETA,
    corr_threshold: float = DEFAULT_CORR_THRESHOLD,
    max_suspects: int = DEFAULT_MAX_SUSPECTS,
) -> list[DivergenceFlag]:
    """The core primitive: lag-align the two streams and return divergence flags.

    ``proxy`` is the agent decision stream, ``outcome`` the delayed
    ground truth; the outcome for day ``t``'s actions is joined from
    ``t + lag_days``.  A window flags when the proxy trends up beyond
    ``+theta`` while the lag-aligned outcome trends down beyond
    ``-theta`` and the two anti-correlate below ``corr_threshold``.
    """
    aligned = align_streams(proxy, outcome, lag_days=lag_days)
    return detect_divergence(
        aligned,
        window=window,
        theta=theta,
        corr_threshold=corr_threshold,
        max_suspects=max_suspects,
    )


def detect_divergence(
    aligned: AlignedStreams,
    window: int = DEFAULT_WINDOW,
    theta: float = DEFAULT_THETA,
    corr_threshold: float = DEFAULT_CORR_THRESHOLD,
    max_suspects: int = DEFAULT_MAX_SUSPECTS,
) -> list[DivergenceFlag]:
    """Scan rolling windows over the aligned join and return merged divergence flags.

    Returns an empty list when the aligned join is shorter than
    ``window``.  Raises ``ValueError`` for a nonsensical parameter
    (window < 2, theta < 0, max_suspects < 1).
    """
    if window < 2:
        raise ValueError(
            f"window 必须 >= 2（当前 {window}）/ window must be >= 2 (got {window})"
        )
    if theta < 0:
        raise ValueError(
            f"theta 必须 >= 0（当前 {theta}）/ theta must be >= 0 (got {theta})"
        )
    if max_suspects < 1:
        raise ValueError(
            f"max_suspects 必须 >= 1（当前 {max_suspects}）/ "
            f"max_suspects must be >= 1 (got {max_suspects})"
        )

    pairs = aligned.pairs
    if len(pairs) < window:
        return []

    sigma_proxy = statistics.pstdev([pair.proxy_value for pair in pairs])
    sigma_outcome = statistics.pstdev([pair.outcome_value for pair in pairs])

    flagged_spans: list[tuple[int, int]] = []
    for start in range(len(pairs) - window + 1):
        chunk = pairs[start : start + window]
        proxy_values = [pair.proxy_value for pair in chunk]
        outcome_values = [pair.outcome_value for pair in chunk]
        if (
            _trend(chunk, sigma_proxy, proxy_values) > theta
            and _trend(chunk, sigma_outcome, outcome_values) < -theta
            and _pearson(proxy_values, outcome_values) < corr_threshold
        ):
            flagged_spans.append((start, start + window - 1))

    return [
        _build_flag(pairs, lo, hi, sigma_proxy, sigma_outcome, max_suspects)
        for lo, hi in _merge_spans(flagged_spans)
    ]


def _trend(chunk: Sequence[DayPair], sigma: float, values: Sequence[float]) -> float:
    """OLS slope of ``values`` per calendar day, normalized by the full-series sigma.

    A constant full series (sigma 0) has no trend by definition.
    """
    if sigma == 0:
        return 0.0
    xs = [pair.t.toordinal() for pair in chunk]
    return statistics.linear_regression(xs, values).slope / sigma


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson correlation; 0.0 when either side lacks variance (no correlation evidence)."""
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return 0.0
    return statistics.correlation(xs, ys)


def _merge_spans(spans: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or directly adjacent [start, end] index spans."""
    merged: list[tuple[int, int]] = []
    for lo, hi in sorted(spans):
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def _build_flag(
    pairs: Sequence[DayPair],
    lo: int,
    hi: int,
    sigma_proxy: float,
    sigma_outcome: float,
    max_suspects: int,
) -> DivergenceFlag:
    """Describe one merged flagged span: stats over the span, top actions by proxy mass."""
    span = pairs[lo : hi + 1]
    proxy_values = [pair.proxy_value for pair in span]
    outcome_values = [pair.outcome_value for pair in span]

    contribution: dict[str, float] = {}
    for pair in span:
        for stat in pair.action_stats:
            contribution[stat.action_id] = (
                contribution.get(stat.action_id, 0.0) + stat.proxy_sum
            )
    suspects = tuple(
        sorted(contribution, key=lambda action: (-contribution[action], action))[
            :max_suspects
        ]
    )

    return DivergenceFlag(
        window=(span[0].t, span[-1].t),
        proxy_trend=_trend(span, sigma_proxy, proxy_values),
        outcome_trend=_trend(span, sigma_outcome, outcome_values),
        corr=_pearson(proxy_values, outcome_values),
        suspect_action_ids=suspects,
    )
