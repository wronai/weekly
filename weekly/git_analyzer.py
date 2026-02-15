"""Module for analyzing Git repositories."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .core.logger import get_logger
from .core.repo_status import RepoStatus

logger = get_logger(__name__)


@dataclass
class CommitStats:
    """Class representing commit statistics."""

    hash: str
    author: str
    date: str
    message: str
    changes: List[Dict[str, str]] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "hash": self.hash,
            "author": self.author,
            "date": self.date,
            "message": self.message,
            "changes": self.changes,
            "additions": self.additions,
            "deletions": self.deletions,
        }


class GitAnalyzer:
    """Class for analyzing Git repositories."""

    def __init__(self, repo_path: Path):
        """Initialize with the path to the Git repository."""
        self.repo_path = Path(repo_path).resolve()

    def get_commit_history(self, since: Optional[datetime] = None) -> List[CommitStats]:
        """Get the commit history of the repository.

        Args:
            since: Only include commits after this date

        Returns:
            List of CommitStats objects
        """
        cmd = [
            "git",
            "log",
            '--pretty=format:{"hash":"%H","author":"%an","date":"%aI","message":"%s"}',
            "--numstat",
        ]

        if since:
            cmd.append(f"--since={since.isoformat()}")

        try:
            result = subprocess.run(
                cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            commits = []
            current_commit = None

            for line in result.stdout.splitlines():
                if line.startswith("{"):
                    if current_commit:
                        commits.append(current_commit)

                    commit_data = json.loads(line)
                    current_commit = CommitStats(
                        hash=commit_data["hash"][:7],
                        author=commit_data["author"],
                        date=commit_data["date"],
                        message=commit_data["message"].replace('"', ""),
                    )
                elif current_commit and line.strip():
                    additions_str, deletions_str, filename = line.split("\t")
                    additions = 0 if additions_str == "-" else int(additions_str)
                    deletions = 0 if deletions_str == "-" else int(deletions_str)

                    current_commit.changes.append(
                        {
                            "file": filename,
                            "additions": str(additions),
                            "deletions": str(deletions),
                        }
                    )
                    current_commit.additions += additions
                    current_commit.deletions += deletions

            if current_commit:
                commits.append(current_commit)

            return commits

        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting commit history: {e}")
            return []

    def analyze(self, since_days: int = 30) -> RepoStatus:
        """Analyze the repository and return a RepoStatus object.

        Args:
            since_days: Number of days to look back for analysis

        Returns:
            RepoStatus object with analysis results
        """
        since = datetime.now() - timedelta(days=since_days)
        commits = self.get_commit_history(since=since)

        # Count contributors
        contributors: Dict[str, int] = {}
        file_changes: Dict[str, int] = {}
        languages: Dict[str, int] = {}

        for commit in commits:
            # Count commits per author
            if commit.author in contributors:
                contributors[commit.author] += 1
            else:
                contributors[commit.author] = 1

            # Count changes per file
            for change in commit.changes:
                filename = change["file"]
                if filename in file_changes:
                    file_changes[filename] += 1
                else:
                    file_changes[filename] = 1

                # Simple language detection by file extension
                ext = Path(filename).suffix
                if ext:
                    if ext in languages:
                        languages[ext] += 1
                    else:
                        languages[ext] = 1

        # Get first commit date
        first_commit_date = None
        if commits:
            first_commit_date = min(commit.date for commit in commits)

        # Create RepoStatus
        return RepoStatus(
            name=self.repo_path.name,
            description=f"Analysis of {self.repo_path.name} repository",
            created_at=first_commit_date or datetime.now().isoformat(),
            last_commit=commits[0].date if commits else "",
            total_commits=len(commits),
            contributors=contributors,
            file_changes=dict(
                sorted(file_changes.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            languages=dict(sorted(languages.items(), key=lambda x: x[1], reverse=True)),
            commits=[commit.to_dict() for commit in commits[:10]],
            todos=["Add more tests", "Update documentation"],
        )
