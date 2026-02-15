"""Tests for the SecurityChecker class."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from weekly.checkers.security import SecurityChecker
from weekly.core.project import Project
from weekly.core.report import CheckResult


@pytest.fixture
def security_checker():
    """Create a SecurityChecker instance for testing."""
    return SecurityChecker()


def test_security_checker_initialization(security_checker):
    """Test that the security checker initializes correctly."""
    assert security_checker.name == "security"
    assert "secrets" in security_checker.description.lower()


def test_security_checker_with_secrets(tmp_path, security_checker):
    """Test security checker with code containing secrets."""
    # Create a Python file with a hardcoded API key
    code = """
def connect():
    api_key = "ghp_1234567890abcdef1234567890abcdef1234"
    return api_key
"""
    test_file = tmp_path / "secrets.py"
    test_file.write_text(code)

    # Run the check
    project = Project(tmp_path)
    result = security_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "warning"
    assert "Found 1 potential secrets" in result.details
    assert any(
        issue["type"] == "GitHub Personal Access Token"
        for issue in result.metadata["issues_data"]["secrets"]
    )


def test_security_checker_with_insecure_functions(tmp_path, security_checker):
    """Test security checker with code using insecure functions."""
    # Create a Python file using eval()
    code = """
def run_code(user_input):
    return eval(user_input)
"""
    test_file = tmp_path / "insecure.py"
    test_file.write_text(code)

    # Run the check
    project = Project(tmp_path)
    result = security_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "warning"
    assert "insecure functions" in result.details
    assert any(
        issue["type"] == "eval()"
        for issue in result.metadata["issues_data"]["insecure_functions"]
    )


def test_security_checker_with_sensitive_files(tmp_path, security_checker):
    """Test security checker with sensitive files committed."""
    # Create a dummy Python file to make it a valid project
    (tmp_path / "app.py").write_text("pass")

    # Create a .env file
    env_file = tmp_path / ".env"
    env_file.write_text("DB_PASSWORD=secret")

    # Run the check
    project = Project(tmp_path)
    result = security_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "warning"
    assert "sensitive files" in result.details
    assert any(
        issue["file"] == ".env"
        for issue in result.metadata["issues_data"]["insecure_files"]
    )


def test_security_checker_passed(tmp_path, security_checker):
    """Test security checker with safe code."""
    # Create a clean Python file
    code = """
def hello():
    print("Hello, World!")
"""
    test_file = tmp_path / "safe.py"
    test_file.write_text(code)

    # Run the check
    project = Project(tmp_path)
    result = security_checker.check(project)

    # Verify the result
    assert isinstance(result, CheckResult)
    assert result.status == "success"
    assert "Security check passed" in result.title
