"""Tests for the ReleaseReadinessChecker class."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from weekly.checkers.release_readiness import ReleaseReadinessChecker
from weekly.core.project import Project
from weekly.core.report import CheckResult


@pytest.fixture
def release_checker():
    """Create a ReleaseReadinessChecker instance for testing."""
    return ReleaseReadinessChecker()


def test_release_checker_initialization(release_checker):
    """Test that the release readiness checker initializes correctly."""
    assert release_checker.name == "release_readiness"
    assert "version consistency" in release_checker.description.lower()


def test_release_checker_consistent_version(tmp_path, release_checker):
    """Test release checker with consistent versions across files."""
    # 1. Create pyproject.toml
    pyproject_content = """
[tool.poetry]
name = "test-project"
version = "1.2.3"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    # 2. Create __init__.py with same version
    src_dir = tmp_path / "test_project"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text('__version__ = "1.2.3"')

    # 3. Create CHANGELOG.md containing version
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.3] - 2026-01-01")

    # 4. Create dist/ directory
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "test_project-1.2.3.tar.gz").write_text("data")

    # Run the check
    project = Project(tmp_path)
    result = release_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "success"
    assert result.metadata["version"] == "1.2.3"
    assert result.metadata["consistent"] is True
    assert result.metadata["updated"] is True
    assert result.metadata["exists"] is True


def test_release_checker_inconsistent_version(tmp_path, release_checker):
    """Test release checker with inconsistent versions."""
    # pyproject.toml has 1.2.3
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nversion = "1.2.3"')

    # __init__.py has 1.2.4
    src_dir = tmp_path / "test_project"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text('__version__ = "1.2.4"')

    # Run the check
    project = Project(tmp_path)
    result = release_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "warning"
    assert result.metadata["consistent"] is False
    assert "Version inconsistency" in result.details


def test_release_checker_missing_changelog_entry(tmp_path, release_checker):
    """Test release checker when current version is missing from changelog."""
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nversion = "1.2.3"')
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.2] - 2025-12-01")

    # Run the check
    project = Project(tmp_path)
    result = release_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "suggestion"
    assert result.metadata["updated"] is False
    assert "Changelog might not be updated" in result.details


def test_release_checker_missing_dist(tmp_path, release_checker):
    """Test release checker when dist/ directory is missing or empty."""
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nversion = "1.2.3"')
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.3]")

    # Run the check
    project = Project(tmp_path)
    result = release_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "suggestion"
    assert result.metadata["exists"] is False
    assert "No distribution files found" in result.details
