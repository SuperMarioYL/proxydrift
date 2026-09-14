"""The bundled synthetic creator-growth replay with planted divergence.

``proxydrift demo`` runs this replay: a 公众号 content agent handed
单篇互动量 (per-article interactions) as its proxy, while the delayed
ground truth — 7 日关注转化 (7-day follow conversion, observed a week
later) — quietly sinks as the agent leans into engagement bait.

The generator is fully deterministic: a fixed calendar, a fixed seed,
and no clock reads.  ``build_demo_replay()`` therefore returns the same
events on every machine, and the committed ``examples/*.csv`` files are
exactly this replay written to disk — what the demo audits in memory is
what `proxydrift audit examples/creator_growth_proxy.csv
examples/creator_growth_outcome.csv` audits from disk.

The planted shape (per decision day ``t``, 63 days) has three regimes:

* benign head (days 0–13) — the agent mostly writes deep originals;
  their interactions slowly decay (the account's natural decline) and
  the conversion holds steady;
* divergence ramp (days 14–29) — the agent's action mix slides toward
  engagement bait, whose articles earn far more interactions, so the
  daily mean proxy climbs from ~100 to ~270 while the conversion
  observed at ``t + lag`` sinks from ~5.3% toward ~2.4%;
* diverged plateau (days 30–62) — the mix stays fully bait; proxy and
  conversion both hold at their new, far-apart levels.

so with the default lag/window thresholds the replay fires one merged
divergence flag across the ramp, naming the bait actions as suspects.
Two early outcome observations are deliberately missing to exercise
coverage-gap reporting.  Everything here is synthetic and labeled as
such — the demo exists to demonstrate the detection mechanism, not real
creator data.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .align import DEFAULT_LAG_DAYS
from .streams import OUTCOME_COLUMNS, PROXY_COLUMNS, OutcomeEvent, ProxyEvent

__all__ = [
    "DEMO_SEED",
    "DEMO_START",
    "DEMO_DECISION_DAYS",
    "DEMO_LAG_DAYS",
    "DEMO_PROXY_LABEL",
    "DEMO_OUTCOME_LABEL",
    "DEMO_STORY",
    "DemoReplay",
    "build_demo_replay",
    "write_demo_csvs",
]

DEMO_SEED = 20260914
DEMO_START = date(2026, 7, 1)
DEMO_DECISION_DAYS = 63
DEMO_LAG_DAYS = DEFAULT_LAG_DAYS  # the outcome arrives a week later

DEMO_PROXY_LABEL = "单篇互动量 (per-article interactions)"
DEMO_OUTCOME_LABEL = "7 日关注转化 (7-day follow conversion, lag-aligned)"

DEMO_STORY = (
    "公众号内容 Agent 被交付「单篇互动量」作为优化目标；"
    "真实结果「7 日关注转化」要 7 天后才到达。"
    "Agent 逐渐把动作质量换成互动诱饵，代理指标一路上涨，"
    "延迟对齐后的转化率持续下沉。"
)

_RAMP_START = 14
_RAMP_END = 30

# action_id -> (weight at mix 0, weight delta to mix 1,
#               proxy value at mix 0, proxy value delta, jitter)
_ACTIONS: dict[str, tuple[float, float, float, float, float]] = {
    "deep_original": (0.75, -0.65, 92.0, 0.0, 8.0),
    "topic_pileup": (0.15, 0.25, 132.0, 92.0, 10.0),
    "title_shock": (0.07, 0.28, 175.0, 195.0, 12.0),
    "emoji_bait": (0.03, 0.12, 178.0, 165.0, 10.0),
}

#: how fast the deep originals' interactions decay during the benign
#: head — the account's natural decline the agent later reverses with
#: bait, which is what makes the head windows definitively un-flagged.
_HEAD_DECAY_PER_DAY = 0.65

#: outcome observations deliberately absent from the replay — the join
#: must surface these as coverage gaps, never interpolate them.
_MISSING_OUTCOME_OFFSETS = (12, 20)


@dataclass(frozen=True)
class DemoReplay:
    """The bundled replay: both streams plus the labels that describe them."""

    proxy_events: tuple[ProxyEvent, ...]
    outcome_events: tuple[OutcomeEvent, ...]
    lag_days: int = DEMO_LAG_DAYS
    proxy_label: str = DEMO_PROXY_LABEL
    outcome_label: str = DEMO_OUTCOME_LABEL


def build_demo_replay(seed: int = DEMO_SEED) -> DemoReplay:
    """Build the deterministic synthetic replay (same seed, same events)."""
    rng = random.Random(seed)

    proxy_events: list[ProxyEvent] = []
    outcome_values: dict[int, float] = {}
    for t in range(DEMO_DECISION_DAYS):
        mix = _bait_mix(t)
        for _ in range(3):  # three articles per day
            action_id, base, delta, jitter = _pick_action(rng, mix, t)
            value = base + delta * mix + rng.uniform(-jitter, jitter)
            proxy_events.append(
                ProxyEvent(
                    t=DEMO_START + timedelta(days=t),
                    action_id=action_id,
                    proxy_value=round(value, 1),
                )
            )
        # the ground truth for day t's actions is observed at t + lag:
        # conversion falls as the day's bait mix rises.
        conversion = 5.35 - 0.0045 * t - 2.95 * mix + rng.uniform(-0.10, 0.10)
        outcome_values[t + DEMO_LAG_DAYS] = round(conversion, 2)

    outcome_events: list[OutcomeEvent] = []
    first_observation = 0
    last_observation = DEMO_DECISION_DAYS - 1 + DEMO_LAG_DAYS
    for o in range(first_observation, last_observation + 1):
        if o in _MISSING_OUTCOME_OFFSETS:
            continue  # planted coverage gap
        if o in outcome_values:
            value = outcome_values[o]
        else:
            # observed before any agent decision's outcome could arrive:
            # the prior steady-state baseline
            value = round(5.35 + rng.uniform(-0.08, 0.08), 2)
        outcome_events.append(
            OutcomeEvent(t=DEMO_START + timedelta(days=o), outcome_value=value)
        )

    return DemoReplay(
        proxy_events=tuple(proxy_events),
        outcome_events=tuple(outcome_events),
    )


def write_demo_csvs(
    proxy_path: str | Path, outcome_path: str | Path, seed: int = DEMO_SEED
) -> tuple[Path, Path]:
    """Write the replay as the two-stream CSV contract; returns both paths.

    The example CSVs shipped in ``examples/`` come from this function,
    so the demo in memory and the audited files on disk are the same
    data.
    """
    replay = build_demo_replay(seed)

    proxy_file = Path(proxy_path)
    proxy_file.parent.mkdir(parents=True, exist_ok=True)
    with proxy_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(PROXY_COLUMNS)
        for event in replay.proxy_events:
            writer.writerow(
                [event.t.isoformat(), event.action_id, event.proxy_value]
            )

    outcome_file = Path(outcome_path)
    outcome_file.parent.mkdir(parents=True, exist_ok=True)
    with outcome_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(OUTCOME_COLUMNS)
        for event in replay.outcome_events:
            writer.writerow([event.t.isoformat(), event.outcome_value])

    return proxy_file, outcome_file


def _bait_mix(t: int) -> float:
    """How hard the agent leans into engagement bait on decision day ``t``."""
    if t < _RAMP_START:
        return 0.0
    if t < _RAMP_END:
        return (t - _RAMP_START) / (_RAMP_END - _RAMP_START)
    return 1.0


def _pick_action(
    rng: random.Random, mix: float, t: int
) -> tuple[str, float, float, float]:
    """Pick one action from the mix-shifted weights; returns its proxy curve.

    Deep originals decay through the benign head (natural decline); the
    bait actions keep their curve — the difference is what the agent is
    later "buying" interactions with.
    """
    weights = {
        action_id: base_w + delta_w * mix
        for action_id, (base_w, delta_w, _, _, _) in _ACTIONS.items()
    }
    action_id = rng.choices(
        list(weights), weights=[weights[a] for a in weights], k=1
    )[0]
    _, _, base_v, delta_v, jitter = _ACTIONS[action_id]
    if action_id == "deep_original":
        base_v -= _HEAD_DECAY_PER_DAY * min(t, _RAMP_START)
    return action_id, base_v, delta_v, jitter
