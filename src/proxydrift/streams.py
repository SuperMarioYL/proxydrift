"""Load and validate the two input streams from CSV files.

ProxyDrift audits an agent decision stream (the proxy metric the agent
was handed) against a delayed ground-truth outcome stream.  Both
streams arrive as strict, minimal CSV files — the contract printed by
``proxydrift --show-template``::

    proxy.csv    one row per agent action
        date          YYYY-MM-DD
        action_id     stable identifier of the action / strategy
        proxy_value   the metric the agent was handed (finite number)

    outcome.csv  one row per day
        date           YYYY-MM-DD
        outcome_value  the delayed ground-truth metric (finite number)

Anything that does not match the contract fails loudly with a bilingual
(zh + en) :class:`StreamValidationError` naming the file, row, and
column.  Row numbers are 1-based with the header as row 1, matching
what a spreadsheet shows.  The loader never guesses, repairs, or
interpolates input.
"""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

__all__ = [
    "PROXY_COLUMNS",
    "OUTCOME_COLUMNS",
    "StreamValidationError",
    "ProxyEvent",
    "OutcomeEvent",
    "load_proxy_stream",
    "load_outcome_stream",
]

PROXY_COLUMNS: tuple[str, ...] = ("date", "action_id", "proxy_value")
OUTCOME_COLUMNS: tuple[str, ...] = ("date", "outcome_value")

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")


class StreamValidationError(ValueError):
    """A CSV file does not match its stream contract; the message is bilingual (zh + en)."""


@dataclass(frozen=True)
class ProxyEvent:
    """One agent action on a day and the proxy value it earned."""

    t: date
    action_id: str
    proxy_value: float


@dataclass(frozen=True)
class OutcomeEvent:
    """One delayed ground-truth observation for a day."""

    t: date
    outcome_value: float


def load_proxy_stream(path: str | Path) -> list[ProxyEvent]:
    """Load and validate a proxy CSV with columns date, action_id, proxy_value."""
    where = str(path)
    events: list[ProxyEvent] = []
    for row_number, row in _data_rows(where, PROXY_COLUMNS):
        events.append(
            ProxyEvent(
                t=_parse_date(row["date"], where, row_number),
                action_id=_require_text(row["action_id"], "action_id", where, row_number),
                proxy_value=_parse_number(row["proxy_value"], "proxy_value", where, row_number),
            )
        )
    if not events:
        raise StreamValidationError(
            f"{where}: 只有表头没有数据行 / header only, no data rows"
        )
    return events


def load_outcome_stream(path: str | Path) -> list[OutcomeEvent]:
    """Load and validate an outcome CSV with columns date, outcome_value."""
    where = str(path)
    events: list[OutcomeEvent] = []
    for row_number, row in _data_rows(where, OUTCOME_COLUMNS):
        events.append(
            OutcomeEvent(
                t=_parse_date(row["date"], where, row_number),
                outcome_value=_parse_number(row["outcome_value"], "outcome_value", where, row_number),
            )
        )
    if not events:
        raise StreamValidationError(
            f"{where}: 只有表头没有数据行 / header only, no data rows"
        )
    return events


def _data_rows(
    where: str, expected: tuple[str, ...]
) -> Iterator[tuple[int, dict[str, str]]]:
    """Yield ``(row_number, column -> stripped value)`` for each data row.

    The header row must match ``expected`` exactly (case-insensitive,
    order-insensitive, no extra or missing columns).
    """
    try:
        with open(where, newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise StreamValidationError(
            f"{where}: 无法读取文件（{exc}）/ cannot read file ({exc})"
        ) from exc

    if not rows:
        raise StreamValidationError(
            f"{where}: 文件为空，缺少表头 / file is empty, missing header row"
        )
    header = [cell.strip().casefold() for cell in rows[0]]
    _check_header(header, expected, where)

    for row_number, cells in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in cells):
            continue  # tolerate blank trailing lines
        if len(cells) != len(expected):
            raise StreamValidationError(
                f"{where}: 第 {row_number} 行有 {len(cells)} 个字段，"
                f"需要 {len(expected)} 个 / "
                f"row {row_number} has {len(cells)} fields, expected {len(expected)}"
            )
        yield row_number, dict(zip(header, (cell.strip() for cell in cells)))


def _check_header(header: list[str], expected: tuple[str, ...], where: str) -> None:
    if not any(header):
        raise StreamValidationError(
            f"{where}: 表头行为空 / header row is empty"
        )
    if len(header) != len(set(header)):
        duplicated = sorted({name for name in header if header.count(name) > 1})
        raise StreamValidationError(
            f"{where}: 表头列重复 {duplicated} / duplicate column(s) in header: {duplicated}"
        )
    if set(header) != set(expected):
        raise StreamValidationError(
            f"{where}: 表头与契约不符，需要 {list(expected)}，实际 {header} / "
            f"header does not match the contract: expected {list(expected)}, got {header}"
        )


def _parse_date(raw: str, where: str, row_number: int) -> date:
    message = (
        f"{where}: 第 {row_number} 行 date 值 {raw!r} 不是合法日期（需要 YYYY-MM-DD）/ "
        f"row {row_number}: 'date' value {raw!r} is not a valid date (expected YYYY-MM-DD)"
    )
    try:
        if not _ISO_DATE.match(raw):
            raise ValueError(raw)
        return date.fromisoformat(raw)
    except ValueError:
        raise StreamValidationError(message) from None


def _parse_number(raw: str, column: str, where: str, row_number: int) -> float:
    message = (
        f"{where}: 第 {row_number} 行 {column} 值 {raw!r} 不是有限数字 / "
        f"row {row_number}: {column!r} value {raw!r} is not a finite number"
    )
    try:
        value = float(raw)
    except ValueError:
        raise StreamValidationError(message) from None
    if not math.isfinite(value):
        raise StreamValidationError(message)
    return value


def _require_text(raw: str, column: str, where: str, row_number: int) -> str:
    if not raw:
        raise StreamValidationError(
            f"{where}: 第 {row_number} 行 {column} 为空 / "
            f"row {row_number}: {column!r} is empty"
        )
    return raw
