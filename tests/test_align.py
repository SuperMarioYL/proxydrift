"""Tests for the lag-alignment join — the m1 engine's alignment semantics.

Focus: lag direction (decision day ``t`` pairs with the outcome observed
at ``t + lag``, never ``t - lag``), daily-bucket aggregation, coverage
gaps (surfaced, never interpolated), and the strict input contracts.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from proxydrift.align import CoverageGap, align_streams
from proxydrift.streams import OutcomeEvent, ProxyEvent

START = date(2026, 7, 1)


def day(offset: int) -> date:
    return START + timedelta(days=offset)


def proxy(offset: int, action_id: str = "act", value: float = 1.0) -> ProxyEvent:
    return ProxyEvent(t=day(offset), action_id=action_id, proxy_value=value)


def outcome(offset: int, value: float) -> OutcomeEvent:
    return OutcomeEvent(t=day(offset), outcome_value=value)


class TestLagDirection:
    def test_decision_day_pairs_with_outcome_observed_later(self):
        """t joins t + lag — the outcome for t's actions arrives later."""
        aligned = align_streams(
            [proxy(10, value=5.0)],
            [outcome(10 - 7, 7.7), outcome(10 + 7, 4.2)],  # t-lag must be ignored
            lag_days=7,
        )
        assert len(aligned.pairs) == 1
        pair = aligned.pairs[0]
        assert pair.t == day(10)
        assert pair.outcome_t == day(17)  # t + 7, not t - 7
        assert pair.outcome_value == 4.2
        assert aligned.gaps == ()

    def test_lag_zero_joins_same_day(self):
        aligned = align_streams(
            [proxy(4, value=2.0)], [outcome(4, 6.5)], lag_days=0
        )
        assert aligned.pairs[0].outcome_t == day(4)
        assert aligned.pairs[0].outcome_value == 6.5

    def test_custom_lag_uses_that_many_days(self):
        aligned = align_streams(
            [proxy(2, value=1.0)],
            [outcome(2 + 21, 3.3), outcome(2 + 7, 8.8)],
            lag_days=21,
        )
        assert aligned.pairs[0].outcome_t == day(23)
        assert aligned.pairs[0].outcome_value == 3.3

    def test_negative_lag_rejected(self):
        with pytest.raises(ValueError, match="lag_days"):
            align_streams([proxy(0)], [outcome(0, 1.0)], lag_days=-1)


class TestDailyBuckets:
    def test_day_mean_and_per_action_stats(self):
        events = [
            proxy(0, "bait", 30.0),
            proxy(0, "deep", 10.0),
            proxy(0, "deep", 20.0),
        ]
        aligned = align_streams(events, [outcome(7, 5.0)], lag_days=7)
        pair = aligned.pairs[0]
        assert pair.proxy_value == pytest.approx(20.0)  # mean of 30, 10, 20
        assert [(s.action_id, s.count, s.proxy_sum) for s in pair.action_stats] == [
            ("bait", 1, 30.0),
            ("deep", 2, 30.0),
        ]

    def test_pairs_sorted_by_decision_day_regardless_of_input_order(self):
        events = [proxy(2), proxy(0), proxy(1)]
        outcomes = [outcome(9, 2.0), outcome(7, 1.0), outcome(8, 3.0)]
        aligned = align_streams(events, outcomes, lag_days=7)
        assert [pair.t for pair in aligned.pairs] == [day(0), day(1), day(2)]
        assert [pair.outcome_value for pair in aligned.pairs] == [1.0, 3.0, 2.0]

    def test_extra_outcome_days_without_proxy_days_create_no_pairs(self):
        aligned = align_streams([proxy(0)], [outcome(k, 1.0) for k in (5, 6, 7)])
        assert len(aligned.pairs) == 1
        assert aligned.gaps == ()


class TestCoverageGaps:
    def test_missing_outcome_is_a_gap_never_interpolated(self):
        aligned = align_streams(
            [proxy(0, value=1.0), proxy(1, value=2.0), proxy(2, value=3.0)],
            [outcome(0 + 7, 5.0), outcome(2 + 7, 4.0)],  # day 1 has none
            lag_days=7,
        )
        assert [pair.t for pair in aligned.pairs] == [day(0), day(2)]
        assert aligned.gaps == (CoverageGap(t=day(1), missing_outcome_date=day(8)),)
        # nothing was carried forward or fabricated for the gap
        assert [pair.outcome_value for pair in aligned.pairs] == [5.0, 4.0]

    def test_every_day_missing_yields_empty_join(self):
        aligned = align_streams([proxy(0), proxy(1)], [outcome(0, 1.0)])
        assert aligned.pairs == ()
        assert len(aligned.gaps) == 2

    def test_duplicate_outcome_with_same_value_is_accepted(self):
        aligned = align_streams(
            [proxy(0)], [outcome(7, 5.0), outcome(7, 5.0)], lag_days=7
        )
        assert aligned.pairs[0].outcome_value == 5.0

    def test_conflicting_outcome_values_rejected(self):
        with pytest.raises(ValueError, match="conflicting"):
            align_streams(
                [proxy(0)], [outcome(7, 5.0), outcome(7, 5.1)], lag_days=7
            )
