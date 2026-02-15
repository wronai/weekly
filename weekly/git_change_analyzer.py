"""Git change analyzer for tracking repository changes and generating changelogs."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CommitInfo:
    """Information about a single commit."""

    hash: str
    author: str
    date: datetime
    message: str
    body: str
    files_changed: List[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    commit_type: str = "other"  # feat, fix, refactor, etc.


@dataclass
class ChangeSummary:
    """Summary of changes in a repository."""

    commits: List[CommitInfo] = field(default_factory=list)
    total_files: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    commit_types: Dict[str, int] = field(default_factory=dict)
    most_changed_files: List[Tuple[str, int]] = field(default_factory=list)


class GitChangeAnalyzer:
    """Analyzes Git repository changes and generates changelogs."""

    def __init__(self, repo_path: Path):
        """Initialize the analyzer.

        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = Path(repo_path)

        # Conventional commit patterns
        self.commit_patterns = {
            "feat": r"^(feat|feature)(\(.+\))?:",
            "fix": r"^(fix|bugfix)(\(.+\))?:",
            "refactor": r"^refactor(\(.+\))?:",
            "docs": r"^docs(\(.+\))?:",
            "style": r"^style(\(.+\))?:",
            "test": r"^test(\(.+\))?:",
            "chore": r"^chore(\(.+\))?:",
            "perf": r"^perf(\(.+\))?:",
            "ci": r"^ci(\(.+\))?:",
            "build": r"^build(\(.+\))?:",
        }

    def _run_git(
        self, command: str, capture_output: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command in the repository.

        Args:
            command: Git command to run
            capture_output: Whether to capture output

        Returns:
            CompletedProcess object
        """
        # Use shlex.split to properly handle quoted arguments
        full_command = ["git", "-C", str(self.repo_path)] + shlex.split(command)
        return subprocess.run(
            full_command, capture_output=capture_output, text=True, cwd=self.repo_path
        )

    def get_commits_since(self, since_date: datetime) -> List[CommitInfo]:
        """Get all commits since a specific date.

        Args:
            since_date: Get commits since this date

        Returns:
            List of CommitInfo objects
        """
        # Get commit log
        since_str = since_date.strftime("%Y-%m-%d")
        format_str = "%H|%an|%ad|%s|%b"

        result = self._run_git(
            f'log --since="{since_str}" --pretty=format:"{format_str}" --date=iso'
        )

        if result.returncode != 0:
            logger.error(f"Error getting git log: {result.stderr}")
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 4)
            if len(parts) < 5:
                continue

            commit_hash, author, date_str, message, body = parts

            # Parse date
            try:
                commit_date = datetime.fromisoformat(date_str.split()[0])
            except (ValueError, IndexError):
                continue

            # Get file changes for this commit
            files_result = self._run_git(
                f"diff-tree --no-commit-id --name-only -r {commit_hash}"
            )
            files = (
                files_result.stdout.strip().split("\n") if files_result.stdout else []
            )

            # Get stats
            stats_result = self._run_git(f"diff-tree --shortstat -r {commit_hash}")
            additions = deletions = 0
            if stats_result.stdout:
                # Parse: " 1 file changed, 5 insertions(+), 2 deletions(-)"
                match = re.search(r"(\d+) insertions?", stats_result.stdout)
                if match:
                    additions = int(match.group(1))
                match = re.search(r"(\d+) deletions?", stats_result.stdout)
                if match:
                    deletions = int(match.group(1))

            # Classify commit type
            commit_type = self._classify_commit(message)

            commits.append(
                CommitInfo(
                    hash=commit_hash,
                    author=author,
                    date=commit_date,
                    message=message,
                    body=body,
                    files_changed=files,
                    additions=additions,
                    deletions=deletions,
                    commit_type=commit_type,
                )
            )

        return commits

    def _classify_commit(self, message: str) -> str:
        """Classify commit type based on message.

        Args:
            message: Commit message

        Returns:
            Commit type string
        """
        for commit_type, pattern in self.commit_patterns.items():
            if re.match(pattern, message, re.IGNORECASE):
                return commit_type

        # Check for common patterns
        message_lower = message.lower()
        if any(word in message_lower for word in ["add", "create", "new", "implement"]):
            return "feat"
        elif any(word in message_lower for word in ["fix", "bug", "error", "issue"]):
            return "fix"
        elif any(word in message_lower for word in ["update", "change", "modify"]):
            return "refactor"
        elif any(word in message_lower for word in ["remove", "delete", "clean"]):
            return "refactor"

        return "other"

    def analyze_changes(self, since_date: datetime) -> ChangeSummary:
        """Analyze changes since a specific date.

        Args:
            since_date: Analyze changes since this date

        Returns:
            ChangeSummary object
        """
        commits = self.get_commits_since(since_date)

        if not commits:
            return ChangeSummary()

        # Calculate statistics
        total_files = len(
            set(file for commit in commits for file in commit.files_changed)
        )
        total_additions = sum(c.additions for c in commits)
        total_deletions = sum(c.deletions for c in commits)

        # Count commit types
        commit_types: Dict[str, int] = {}
        for commit in commits:
            commit_types[commit.commit_type] = (
                commit_types.get(commit.commit_type, 0) + 1
            )

        # Find most changed files
        file_changes: Dict[str, int] = {}
        for commit in commits:
            for file in commit.files_changed:
                file_changes[file] = file_changes.get(file, 0) + 1

        most_changed_files = sorted(
            file_changes.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return ChangeSummary(
            commits=commits,
            total_files=total_files,
            total_additions=total_additions,
            total_deletions=total_deletions,
            commit_types=commit_types,
            most_changed_files=most_changed_files,
        )

    def generate_changelog_with_git_cliff(
        self, since_date: datetime, output_path: Path
    ) -> bool:
        """Generate changelog using git-cliff.

        Args:
            since_date: Generate changelog since this date
            output_path: Path to save the changelog

        Returns:
            True if successful
        """
        since_str = since_date.strftime("%Y-%m-%d")

        # Create a minimal cliff config
        config_content = """
[changelog]
header = '''
# Changelog

All notable changes to this project will be documented in this file.

'''
trim = true

[git]
conventional_commits = true
filter_unconventional = false
split_commits = false
commit_preprocessors = []
commit_parsers = [
  { pattern = "^feat", group = "Features" },
  { pattern = "^fix", group = "Bug Fixes" },
  { pattern = "^refactor", group = "Refactoring" },
  { pattern = "^docs", group = "Documentation" },
  { pattern = "^style", group = "Styling" },
  { pattern = "^test", group = "Testing" },
  { pattern = "^chore", group = "Chore" },
  { pattern = "^perf", group = "Performance" },
  { pattern = "^ci", group = "Continuous Integration" },
  { pattern = "^build", group = "Build" },
]
filter_commits = false
tag_pattern = "v[0-9]*"
ignore_tags = ""
topo_order = false
sort_commits = "oldest"
"""

        config_path = self.repo_path / ".cliff.toml"
        try:
            # Write config
            with open(config_path, "w") as f:
                f.write(config_content)

            # Compute a git RANGE for git-cliff.
            # git-cliff v2.x uses a positional Git revision range (e.g. A^..HEAD).
            # We pick the oldest commit that is >= since_str.
            oldest_commit = (
                self._run_git(
                    f'rev-list --reverse --since="{since_str}" HEAD',
                    capture_output=True,
                )
                .stdout.strip()
                .splitlines()[:1]
            )
            if not oldest_commit:
                return False
            oldest_commit_hash = oldest_commit[0].strip()
            
            # Check if this is the root commit (has no parents)
            is_root = self._run_git(f"rev-list --parents -n 1 {oldest_commit_hash}").stdout.strip() == oldest_commit_hash
            
            if is_root:
                git_range = oldest_commit_hash + "..HEAD"
                # If there's only one commit, HEAD is oldest_commit_hash, so range might be empty.
                # In that case, we can just use HEAD.
                if self._run_git("rev-parse HEAD").stdout.strip() == oldest_commit_hash:
                    git_range = oldest_commit_hash
            else:
                git_range = f"{oldest_commit_hash}^..HEAD"

            # Run git-cliff in the repository
            try:
                result = subprocess.run(
                    ["git-cliff", git_range, "--config", str(config_path)],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    cwd=self.repo_path,
                )
            except FileNotFoundError:
                logger.warning(
                    "git-cliff not found; skipping git-cliff changelog generation"
                )
                return False
            except subprocess.SubprocessError as e:
                logger.warning(f"git-cliff failed to run: {e}")
                return False

            if result.returncode == 0:
                # Save to output path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(result.stdout)
                return True
            else:
                logger.error(f"git-cliff error: {result.stderr}")
                return False
        finally:
            # Clean up config
            if config_path.exists():
                config_path.unlink()

    def generate_summary_report(self, summary: ChangeSummary) -> str:
        """Generate a text summary of changes.

        Args:
            summary: ChangeSummary object

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("## 📊 Change Summary")
        lines.append("")
        lines.append(f"- **Total Commits:** {len(summary.commits)}")
        lines.append(f"- **Files Changed:** {summary.total_files}")
        lines.append(f"- **Lines Added:** {summary.total_additions}")
        lines.append(f"- **Lines Removed:** {summary.total_deletions}")
        lines.append("")

        if summary.commit_types:
            lines.append("### Commit Types")
            lines.append("")
            for commit_type, count in sorted(
                summary.commit_types.items(), key=lambda x: x[1], reverse=True
            ):
                emoji = {
                    "feat": "✨",
                    "fix": "🐛",
                    "refactor": "♻️",
                    "docs": "📚",
                    "style": "💄",
                    "test": "✅",
                    "chore": "🔧",
                    "perf": "⚡",
                    "ci": "👷",
                    "build": "📦",
                    "other": "📝",
                }.get(commit_type, "📝")
                lines.append(f"- {emoji} **{commit_type.title()}:** {count}")
            lines.append("")

        if summary.most_changed_files:
            lines.append("### Most Changed Files")
            lines.append("")
            for file_path, count in summary.most_changed_files[:5]:
                lines.append(f"- `{file_path}` ({count} commits)")
            lines.append("")

        # Recent commits
        lines.append("### Recent Commits")
        lines.append("")
        for commit in summary.commits[:10]:
            date_str = commit.date.strftime("%Y-%m-%d")
            lines.append(f"- **{date_str}** - {commit.message}")
            lines.append(f"  - Author: {commit.author}")
            lines.append(
                f"  - Files: {len(commit.files_changed)} (+{commit.additions}/-{commit.deletions})"
            )
            lines.append("")

        return "\n".join(lines)
