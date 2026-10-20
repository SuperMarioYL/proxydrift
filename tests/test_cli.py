"""Tests for the proxydrift CLI contract.

Focus: the documented exit codes (0 clean / 1 flagged / 2 usage or input
error) on the paths a user hits directly — version, template, and the
error contract for an unwritable --report path, which must exit cleanly
instead of escaping as a traceback.
"""

from __future__ import annotations

import pytest

import proxydrift
from proxydrift.cli import EXIT_ERROR, EXIT_OK, main


REPO = "examples/creator_growth_proxy.csv"
OUTCOME = "examples/creator_growth_outcome.csv"


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
