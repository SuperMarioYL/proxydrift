"""Version lockstep: VERSION file, pyproject.toml, and __version__ agree.

The release tag is cut from the repo-root VERSION file; the package
metadata comes from pyproject.toml; the CLI prints
``proxydrift.__version__``.  These three must never drift apart.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import proxydrift

REPO_ROOT = Path(__file__).resolve().parents[1]


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
