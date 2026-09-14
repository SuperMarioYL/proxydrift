"""Tests for the windowed divergence detection — the m1 engine's flag semantics.

Focus: the flag predicate (proxy trending up beyond θ while the
lag-aligned outcome trends down beyond −θ and the two anti-correlate),
negative controls for each arm, window merging, suspect ranking, the
mandatory correlational verdict, and the bundled synthetic replay with
its planted divergence.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from proxydrift import audit
from proxydrift.align import align_streams
from proxydrift.demo_data import build_demo_replay
from proxydrift.divergence import (
    CORRELATIONAL_VERDICT,
    DEFAULT_WINDOW,
    DivergenceFlag,
    _merge_spans,
    detect_divergence,
)
from proxydrift.streams import OutcomeEvent, ProxyEvent, load_outcome_stream, load_proxy_stream

START = date(2026, 7, 1)
REPO_ROOT = Path(__file__).resolve().parents[1]


def day(offset: int) -> date:
    return START + timedelta(days=offset)


def aligned_series(days: int, proxy_fn, outcome_fn, lag_days: int = 7):
    """One event per day; the outcome for day t is observed at t + lag."""
    proxy = [ProxyEvent(day(t), "agent", proxy_fn(t)) for t in range(days)]
    outcome = [
        OutcomeEvent(day(t + lag_days), outcome_fn(t)) for t in range(days)
    ]
    return align_streams(proxy, outcome, lag_days=lag_days)


def monotone_divergence(days: int = 30):
    """A clean planted divergence: proxy up, outcome down, corr = -1."""
    return aligned_series(
        days, lambda t: 100.0 + 3.0 * t, lambda t: 5.0 - 0.08 * t
    )


class TestFlagPredicate:
    def test_planted_divergence_fires_with_signed_trends(self):
        flags = detect_divergence(monotone_divergence())
        assert len(flags) == 1
        flag = flags[0]
        assert flag.proxy_trend > 0.05
        assert flag.outcome_trend < -0.05
        assert flag.corr < -0.3
        assert flag.window == (day(0), day(29))
        assert flag.verdict == CORRELATIONAL_VERDICT

    def test_negative_control_both_streams_improving(self):
        """Proxy and outcome rising together is alignment, not divergence."""
        aligned = aligned_series(
            30, lambda t: 100.0 + 3.0 * t, lambda t: 5.0 + 0.08 * t
        )
        assert detect_divergence(aligned) == []

    def test_negative_control_flat_proxy(self):
        """A sinking outcome alone never fires — the proxy must climb."""
        aligned = aligned_series(
            30, lambda t: 100.0, lambda t: 5.0 - 0.08 * t
        )
        assert detect_divergence(aligned) == []

    def test_negative_control_flat_outcome(self):
        """A climbing proxy alone never fires — the outcome must sink."""
        aligned = aligned_series(
            30, lambda t: 100.0 + 3.0 * t, lambda t: 5.0
        )
        assert detect_divergence(aligned) == []

    def test_theta_threshold_gates_the_trend_arm(self):
        """Same planted divergence, trend threshold beyond the slopes."""
        assert detect_divergence(monotone_divergence(), theta=0.5) == []

    def test_correlation_threshold_gates_the_corr_arm(self):
        """Trends pass but the window only weakly anti-correlates."""
        zigzag = aligned_series(
            30,
            lambda t: 100.0 + 4.0 * t,
            lambda t: 5.0 - 0.07 * t + (0.9 if t % 2 == 0 else -0.9),
        )
        assert len(detect_divergence(zigzag)) == 1  # corr ≈ -0.59 < -0.3
        assert detect_divergence(zigzag, corr_threshold=-0.75) == []

    def test_series_shorter_than_window_scans_nothing(self):
        aligned = monotone_divergence(days=10)
        assert len(aligned.pairs) < DEFAULT_WINDOW
        assert detect_divergence(aligned) == []


class TestWindowMerging:
    def test_every_window_flagging_merges_into_one_flag(self):
        aligned = monotone_divergence(40)
        flags = detect_divergence(aligned)
        assert len(flags) == 1
        assert flags[0].window == (aligned.pairs[0].t, aligned.pairs[-1].t)

    def test_disjoint_spans_stay_separate(self):
        assert _merge_spans([(0, 5), (7, 12)]) == [(0, 5), (7, 12)]

    def test_overlapping_and_adjacent_spans_merge(self):
        assert _merge_spans([(0, 10), (5, 15)]) == [(0, 15)]
        assert _merge_spans([(0, 5), (6, 9), (20, 25), (21, 22)]) == [
            (0, 9),
            (20, 25),
        ]

    def test_unsorted_input_spans_are_sorted_first(self):
        assert _merge_spans([(6, 9), (0, 5)]) == [(0, 9)]


class TestSuspectRanking:
    @staticmethod
    def _bait_mix_series():
        """Rising daily mean via action mix; per-action masses are known."""
        curves = {
            "bait_a": 10.0,
            "bait_b": 6.0,
            "tie_c": 4.0,
            "tie_d": 4.0,
            "quiet_e": 1.0,
        }
        proxy = [
            ProxyEvent(day(t), action_id, base * (1.0 + 0.05 * t))
            for t in range(30)
            for action_id, base in curves.items()
        ]
        outcome = [
            OutcomeEvent(day(t + 7), 5.0 - 0.08 * t) for t in range(30)
        ]
        return align_streams(proxy, outcome, lag_days=7)

    def test_suspects_ranked_by_proxy_mass_then_id(self):
        flags = detect_divergence(self._bait_mix_series())
        assert len(flags) == 1
        assert flags[0].suspect_action_ids == (
            "bait_a",
            "bait_b",
            "tie_c",  # tie_c and tie_d carry equal mass; id breaks it
        )

    def test_max_suspects_limits_the_list(self):
        flags = detect_divergence(self._bait_mix_series(), max_suspects=1)
        assert flags[0].suspect_action_ids == ("bait_a",)


class TestParameterValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"window": 1},
            {"theta": -0.01},
            {"max_suspects": 0},
        ],
    )
    def test_nonsense_parameters_rejected(self, kwargs):
        with pytest.raises(ValueError):
            detect_divergence(monotone_divergence(), **kwargs)


class TestBundledReplay:
    """The demo replay is a shipped contract: one planted flag, bait suspects."""

    def test_replay_is_deterministic(self):
        first = build_demo_replay()
        second = build_demo_replay()
        assert first.proxy_events == second.proxy_events
        assert first.outcome_events == second.outcome_events

    def test_replay_fires_exactly_one_flag_naming_the_bait(self):
        replay = build_demo_replay()
        flags = audit(replay.proxy_events, replay.outcome_events, lag_days=7)
        assert len(flags) == 1
        flag = flags[0]
        assert flag.suspect_action_ids == (
            "title_shock",
            "topic_pileup",
            "emoji_bait",
        )
        assert flag.proxy_trend > 0
        assert flag.outcome_trend < 0
        assert flag.corr < -0.3
        assert flag.verdict == CORRELATIONAL_VERDICT

    def test_replay_reports_its_planted_coverage_gaps(self):
        replay = build_demo_replay()
        aligned = align_streams(
            replay.proxy_events, replay.outcome_events, lag_days=7
        )
        assert len(aligned.pairs) == 61
        assert len(aligned.gaps) == 2

    def test_wrong_lag_destroys_the_planted_alignment(self):
        """The flag depends on the lag join, not on any single trend."""
        replay = build_demo_replay()
        assert (
            audit(replay.proxy_events, replay.outcome_events, lag_days=30) == []
        )


class TestShippedExamples:
    """m1 acceptance: the committed example CSVs trigger the flag."""

    def test_examples_trigger_one_flag_at_default_lag(self):
        proxy = load_proxy_stream(REPO_ROOT / "examples/creator_growth_proxy.csv")
        outcome = load_outcome_stream(
            REPO_ROOT / "examples/creator_growth_outcome.csv"
        )
        flags = audit(proxy, outcome, lag_days=7)
        assert len(flags) == 1
        assert isinstance(flags[0], DivergenceFlag)

    def test_examples_match_the_demo_replay(self):
        """examples/ is the demo replay on disk — one source of truth."""
        replay = build_demo_replay()
        proxy = load_proxy_stream(REPO_ROOT / "examples/creator_growth_proxy.csv")
        outcome = load_outcome_stream(
            REPO_ROOT / "examples/creator_growth_outcome.csv"
        )
        assert proxy == list(replay.proxy_events)
        assert outcome == list(replay.outcome_events)
