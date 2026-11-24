"""Version lockstep: VERSION file, pyproject.toml, and __version__ agree.

The release tag is cut from the repo-root VERSION file; the package
metadata comes from pyproject.toml; the CLI prints
``proxydrift.__version__``.  These three must never drift apart, and the
HTML report must be stamped with that same value — not with whatever
proxydrift distribution the interpreter happens to see installed.
"""

from __future__ import annotations

import importlib.metadata
import tomllib
from datetime import date, timedelta
from pathlib import Path

import proxydrift
from proxydrift import (
    OutcomeEvent,
    ProxyEvent,
    align_streams,
    build_report_html,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _tiny_report_html() -> str:
    """A report built from a 3-day join: enough to render, no flags."""
    start = date(2026, 1, 1)
    aligned = align_streams(
        [ProxyEvent(start + timedelta(days=t), "act", 10.0 + t) for t in range(3)],
        [
            OutcomeEvent(start + timedelta(days=t + 7), 5.0 - 0.1 * t)
            for t in range(3)
        ],
        lag_days=7,
    )
    return build_report_html(aligned, [], window=14)


def test_version_file_matches_package_version():
    version_file = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version_file == proxydrift.__version__


def test_pyproject_version_matches_package_version():
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["version"] == proxydrift.__version__


def test_version_is_semver():
    parts = proxydrift.__version__.split(".")
    assert len(parts) == 3 and all(part.isdigit() for part in parts)


def test_report_footer_names_the_running_package_version(monkeypatch):
    """A stale installed distribution must not relabel the report."""
    monkeypatch.setattr(
        importlib.metadata, "version", lambda name: "0.1.0"
    )
    html = _tiny_report_html()
    assert f"ProxyDrift v{proxydrift.__version__}" in html
    assert "ProxyDrift v0.1.0" not in html


def test_report_footer_names_the_version_without_installed_metadata(monkeypatch):
    """Running from a source tree (no dist metadata) still stamps the version."""
    def _missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _missing)
    html = _tiny_report_html()
    assert f"ProxyDrift v{proxydrift.__version__}" in html
