"""Lag-shift the outcome stream and join both streams on daily buckets.

The outcome stream is delayed ground truth: the outcome produced by the
agent's actions on day ``t`` is observed on day ``t + lag_days``.  The
join therefore pairs each proxy day ``t`` with the outcome value
observed at ``t + lag_days`` — never the other way round.

Both streams are bucketed per calendar day.  A proxy day aggregates all
of the agent's actions that day into a mean proxy value plus per-action
contribution stats (kept for suspect attribution in
``divergence.detect_divergence``).  Proxy days whose lag-shifted outcome
is missing are dropped from the join and surfaced as
:class:`CoverageGap` entries — the join never interpolates, carries
values forward, or silently drops days.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from .streams import OutcomeEvent, ProxyEvent

__all__ = [
    "DEFAULT_LAG_DAYS",
    "ActionStat",
    "DayPair",
    "CoverageGap",
    "AlignedStreams",
    "align_streams",
]

DEFAULT_LAG_DAYS = 7


@dataclass(frozen=True)
class ActionStat:
    """One action's usage on one day: how often it ran and the proxy mass it carried."""

    action_id: str
    count: int
    proxy_sum: float


@dataclass(frozen=True)
class DayPair:
    """One joined day: the agent's decisions on ``t`` and their lag-shifted outcome.

    ``outcome_t`` is ``t + lag_days`` — the day the ground truth for
    ``t``'s actions was actually observed.
    """

    t: date
    proxy_value: float  # mean proxy value across the day's events
    action_stats: tuple[ActionStat, ...]  # that day's actions, sorted by action_id
    outcome_t: date
    outcome_value: float


@dataclass(frozen=True)
class CoverageGap:
    """A proxy day whose lag-shifted outcome is missing from the outcome stream."""

    t: date  # the decision day
    missing_outcome_date: date  # t + lag_days, absent from the outcome stream


@dataclass(frozen=True)
class AlignedStreams:
    """The lag-aligned daily join, plus every coverage gap the join dropped."""

    lag_days: int
    pairs: tuple[DayPair, ...]  # joined days, sorted by decision day t
    gaps: tuple[CoverageGap, ...]  # dropped days, sorted by decision day t


def align_streams(
    proxy: Sequence[ProxyEvent],
    outcome: Sequence[OutcomeEvent],
    lag_days: int = DEFAULT_LAG_DAYS,
) -> AlignedStreams:
    """Shift the outcome stream back by ``lag_days`` and join on daily buckets.

    Raises ``ValueError`` when ``lag_days`` is negative, or when the
    outcome stream carries conflicting values for the same date (the
    join requires exactly one ground-truth value per day).
    """
    if lag_days < 0:
        raise ValueError(
            f"lag_days 不能为负 / lag_days must be >= 0, got {lag_days}"
        )

    proxy_actions: dict[date, dict[str, list[float]]] = {}
    for event in proxy:
        by_action = proxy_actions.setdefault(event.t, {})
        by_action.setdefault(event.action_id, []).append(event.proxy_value)

    outcome_by_day: dict[date, float] = {}
    for event in outcome:
        previous = outcome_by_day.setdefault(event.t, event.outcome_value)
        if previous != event.outcome_value:
            raise ValueError(
                f"outcome 流在 {event.t} 有冲突取值 {previous} 与 {event.outcome_value} / "
                f"outcome stream has conflicting values on {event.t}: "
                f"{previous} vs {event.outcome_value}"
            )

    shift = timedelta(days=lag_days)
    pairs: list[DayPair] = []
    gaps: list[CoverageGap] = []
    for t in sorted(proxy_actions):
        actions = proxy_actions[t]
        event_count = sum(len(values) for values in actions.values())
        proxy_total = sum(sum(values) for values in actions.values())
        action_stats = tuple(
            ActionStat(action_id=action_id, count=len(values), proxy_sum=sum(values))
            for action_id, values in sorted(actions.items())
        )
        outcome_t = t + shift
        if outcome_t in outcome_by_day:
            pairs.append(
                DayPair(
                    t=t,
                    proxy_value=proxy_total / event_count,
                    action_stats=action_stats,
                    outcome_t=outcome_t,
                    outcome_value=outcome_by_day[outcome_t],
                )
            )
        else:
            gaps.append(CoverageGap(t=t, missing_outcome_date=outcome_t))
    return AlignedStreams(lag_days=lag_days, pairs=tuple(pairs), gaps=tuple(gaps))
