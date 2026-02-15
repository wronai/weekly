"""Tests for the PackagingChecker class."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from weekly.checkers.packaging import PackagingChecker
from weekly.core.project import Project
from weekly.core.report import CheckResult


@pytest.fixture
def packaging_checker():
    """Create a PackagingChecker instance for testing."""
    return PackagingChecker()


def test_packaging_checker_initialization(packaging_checker):
    """Test that the packaging checker initializes correctly."""
    assert packaging_checker.name == "packaging"
    assert "PEP 517/518" in packaging_checker.description


def test_packaging_checker_modern_poetry(tmp_path, packaging_checker):
    """Test packaging checker with a modern Poetry project."""
    pyproject_content = """
[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "A test project"
authors = ["Test User <test@example.com>"]
license = "Apache-2.0"
readme = "README.md"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)
    (tmp_path / "README.md").write_text("# Test Project")

    # Run the check
    project = Project(tmp_path)
    result = packaging_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "success"
    assert "setup looks good" in result.title
    assert result.metadata["pep517"] is True
    assert result.metadata["build_backend"] == "poetry.core.masonry.api"


def test_packaging_checker_missing_build_system(tmp_path, packaging_checker):
    """Test packaging checker with missing build-system section."""
    pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    # Run the check
    project = Project(tmp_path)
    result = packaging_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "warning"
    assert "missing [build-system]" in result.details


def test_packaging_checker_missing_metadata(tmp_path, packaging_checker):
    """Test packaging checker with missing essential metadata."""
    pyproject_content = """
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "test-project"
# version and description missing
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    # Run the check
    project = Project(tmp_path)
    result = packaging_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "warning"
    assert "version" in result.metadata["missing"]
    assert "description" in result.metadata["missing"]
