"""Integration tests for the Git scanner report generation."""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from weekly.cli import main
from weekly.git_scanner import GitScanner


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary Git repository for testing."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()

    # Initialize Git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
    )

    # Create some files
    (repo_path / "README.md").write_text("# Test Repo\nThis is a test repository.")
    (repo_path / "requirements.txt").write_text("requests==2.28.1\npytest")
    (repo_path / "app.py").write_text(
        "def main():\n    print('hello')\n\nif __name__ == '__main__':\n    main()"
    )

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: initial commit"], cwd=repo_path, check=True
    )

    return repo_path


def test_scan_command_generates_reports(temp_git_repo, tmp_path):
    """Test that the scan command generates HTML and Markdown reports."""
    runner = CliRunner()
    output_dir = tmp_path / "reports"

    # Run scan command
    result = runner.invoke(
        main,
        [
            "scan",
            str(temp_git_repo.parent),
            "--output",
            str(output_dir),
            "--no-recursive",
        ],
    )

    assert result.exit_code == 0

    # Check that reports were generated
    # Expected path: output_dir / "" / repo_name / "latest.html"
    # Note: repo.org is empty if repo is at root_dir
    repo_name = temp_git_repo.name
    report_dir = output_dir / repo_name

    assert report_dir.exists()
    assert (report_dir / "latest.html").exists()
    assert (report_dir / "latest.md").exists()
    assert (report_dir / "latest.llm.md").exists()
    assert (report_dir / "changelog.md").exists()
    assert (output_dir / "summary.html").exists()

    # Check content of the report
    report_content = (report_dir / "latest.html").read_text()
    assert repo_name in report_content
    assert "Check Results" in report_content


def test_scan_with_since_filter(temp_git_repo, tmp_path):
    """Test the --since filter in the scan command."""
    runner = CliRunner()
    output_dir = tmp_path / "reports_since"

    # Case 1: Since tomorrow (should find nothing)
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    result = runner.invoke(
        main,
        [
            "scan",
            str(temp_git_repo.parent),
            "--output",
            str(output_dir),
            "--since",
            tomorrow,
            "--no-recursive",
        ],
    )

    assert result.exit_code == 0
    assert "No repositories found or no changes detected" in result.output

    # Case 2: Since yesterday (should find our commit)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    result = runner.invoke(
        main,
        [
            "scan",
            str(temp_git_repo.parent),
            "--output",
            str(output_dir),
            "--since",
            yesterday,
            "--no-recursive",
        ],
    )

    assert result.exit_code == 0
    assert "Generated reports for 1 repositories" in result.output
