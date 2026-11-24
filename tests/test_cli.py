"""Tests for the proxydrift CLI contract.

Focus: the documented exit codes (0 clean / 1 flagged / 2 usage or input
error) on the paths a user hits directly — version, template, and the
error contract for an unwritable --report path, which must exit cleanly
instead of escaping as a traceback.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

import proxydrift
from proxydrift import OutcomeEvent, ProxyEvent, align_streams, build_report_html
from proxydrift.cli import EXIT_ERROR, EXIT_OK, main


REPO = "examples/creator_growth_proxy.csv"
OUTCOME = "examples/creator_growth_outcome.csv"


def _write_streams(tmp_path, proxy_days, outcome_days, lag_days):
    """Write a proxy/outcome pair whose join is exactly ``proxy_days`` days long.

    The outcome is observed ``lag_days`` after each decision day, so
    ``outcome_days`` decides how many of the proxy days actually join.
    """
    start = date(2026, 1, 1)
    proxy_csv = tmp_path / "proxy.csv"
    outcome_csv = tmp_path / "outcome.csv"
    proxy_csv.write_text(
        "date,action_id,proxy_value\n"
        + "".join(
            f"{(start + timedelta(days=t)).isoformat()},act,{10.0 + t}\n"
            for t in range(proxy_days)
        ),
        encoding="utf-8",
    )
    outcome_csv.write_text(
        "date,outcome_value\n"
        + "".join(
            f"{(start + timedelta(days=t + lag_days)).isoformat()},"
            f"{5.0 - 0.1 * t}\n"
            for t in range(outcome_days)
        ),
        encoding="utf-8",
    )
    return proxy_csv, outcome_csv


class TestUnmeasurableAudit:
    """No window scanned is not "no flags": it is an audit that measured nothing."""

    def test_zero_joined_days_exits_2_without_report(self, tmp_path, capsys):
        proxy_csv, outcome_csv = _write_streams(tmp_path, 8, 3, lag_days=30)
        report = tmp_path / "report.html"
        argv = [
            "audit",
            str(proxy_csv),
            str(outcome_csv),
            "--lag",
            "30",
            "--no-llm",
            "--report",
            str(report),
        ]
        with pytest.raises(SystemExit) as excinfo:
            main(argv)
        assert excinfo.value.code == EXIT_ERROR
        captured = capsys.readouterr()
        assert "错误 error" in captured.err
        assert "joined decision days = 0" not in captured.out
        assert not report.exists()

    def test_join_shorter_than_window_exits_2(self, tmp_path, capsys):
        proxy_csv, outcome_csv = _write_streams(tmp_path, 10, 3, lag_days=7)
        with pytest.raises(SystemExit) as excinfo:
            main(
                [
                    "audit",
                    str(proxy_csv),
                    str(outcome_csv),
                    "--no-llm",
                    "--no-report",
                ]
            )
        assert excinfo.value.code == EXIT_ERROR
        assert "错误 error" in capsys.readouterr().err

    def test_unmeasurable_report_is_not_painted_green(self):
        start = date(2026, 1, 1)
        proxy = [ProxyEvent(start + timedelta(days=t), "act", 10.0 + t) for t in range(5)]
        outcome = [
            OutcomeEvent(start + timedelta(days=t + 7), 5.0 - 0.1 * t) for t in range(5)
        ]
        aligned = align_streams(proxy, outcome, lag_days=7)
        html = build_report_html(aligned, [], window=14)
        assert 'class="n good"' not in html
        assert "no window was scanned" in html
        assert "未亮旗 / no flags fired" not in html


class TestBasicCommands:
    def test_version_prints_package_version(self, capsys):
        assert main(["--version"]) == EXIT_OK
        assert proxydrift.__version__ in capsys.readouterr().out

    def test_show_template_prints_contract(self, capsys):
        assert main(["--show-template"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "date,action_id,proxy_value" in out
        assert "date,outcome_value" in out

    def test_no_command_prints_help_and_exits_2(self, capsys):
        assert main([]) == EXIT_ERROR


class TestReportErrorContract:
    def test_unwritable_report_path_exits_2_without_traceback(self, tmp_path, capsys):
        """A report path whose parent is a file must fail as a usage error
        (exit 2, bilingual message), not as an uncaught OSError."""
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("a file, so mkdir under it cannot succeed", encoding="utf-8")
        bad_report = blocker / "report.html"
        with pytest.raises(SystemExit) as excinfo:
            main(
                [
                    "audit",
                    REPO,
                    OUTCOME,
                    "--no-llm",
                    "--report",
                    str(bad_report),
                ]
            )
        assert excinfo.value.code == EXIT_ERROR
        captured = capsys.readouterr()
        assert "错误 error" in captured.err or "error" in captured.err.lower()

    def test_clean_audit_writes_report_and_exits_1(self, tmp_path, capsys):
        """The bundled replay carries a planted flag, so exit 1 with a report."""
        report = tmp_path / "out" / "report.html"
        assert (
            main(["audit", REPO, OUTCOME, "--no-llm", "--report", str(report)])
            == 1
        )
        assert report.exists()
        assert "ProxyDrift 背离审计" in capsys.readouterr().out
