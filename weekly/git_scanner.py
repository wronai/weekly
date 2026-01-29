"""Module for scanning Git repositories and generating reports."""
from __future__ import annotations

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
import subprocess
import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from weekly.git_report import GitReportGenerator, RepoInfo, CheckResult as ReportCheckResult
from weekly.git_change_analyzer import GitChangeAnalyzer, ChangeSummary

from weekly.core.project import Project
from weekly.core.report import CheckResult as CoreCheckResult


@dataclass
class GitRepo:
    """Represents a Git repository with its metadata."""
    
    path: Path
    name: str
    org: str = ""
    last_commit_date: Optional[datetime] = None
    has_changes: bool = False
    branch: str = "main"
    remote_url: str = ""
    
    def __post_init__(self):
        """Initialize repository metadata."""
        if not hasattr(self, 'path') or not self.path:
            raise ValueError("path is required")
            
        if not hasattr(self, 'name') or not self.name:
            raise ValueError("name is required")
            
        self.path = Path(self.path).resolve()
        
        # Set default values for optional fields
        if not hasattr(self, 'org') or self.org is None:
            self.org = ""
            
        if not hasattr(self, 'last_commit_date') or self.last_commit_date is None:
            self.last_commit_date = None
            
        if not hasattr(self, 'has_changes') or self.has_changes is None:
            self.has_changes = False
            
        if not hasattr(self, 'branch') or not self.branch:
            self.branch = "main"
            
        if not hasattr(self, 'remote_url') or self.remote_url is None:
            self.remote_url = ""

        self._extract_metadata()
    
    def _extract_metadata(self) -> None:
        """Extract metadata from the Git repository."""
        try:
            # Get the current branch
            result = self._run_git("rev-parse --abbrev-ref HEAD")
            if result.returncode == 0 and result.stdout.strip():
                self.branch = result.stdout.strip()
            
            # Get the last commit date
            result = self._run_git("log -1 --format=%cd --date=iso")
            if result.returncode == 0 and result.stdout.strip():
                self.last_commit_date = datetime.strptime(
                    result.stdout.strip().split()[0], 
                    "%Y-%m-%d"
                )
            
            # Get the remote URL
            result = self._run_git("remote get-url origin")
            if result.returncode == 0 and result.stdout.strip():
                self.remote_url = result.stdout.strip()
        except Exception as e:
            pass
    
    def has_recent_changes(self, since: datetime) -> bool:
        """Check if the repository has changes since a specific date."""
        if not self.last_commit_date:
            return False
        # Compare dates only, ignoring time
        return self.last_commit_date.date() >= since.date()
    
    def _run_git(self, command: str) -> subprocess.CompletedProcess:
        """Run a git command in the repository."""
        try:
            return subprocess.run(
                ["git"] + shlex.split(command),
                cwd=self.path,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            return subprocess.CompletedProcess(args=command, returncode=1)


@dataclass
class ScanResult:
    """Represents the result of scanning a repository."""
    
    repo: 'GitRepo'
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    change_summary: Optional[ChangeSummary] = None
    
    def __post_init__(self):
        """Initialize the scan result with default values."""
        # Ensure results is always a dictionary
        if self.results is None:
            self.results = {}
    
    def to_dict(self) -> Dict:
        """Convert the result to a dictionary."""
        serialized_results: Dict[str, Any] = {}
        for name, value in self.results.items():
            if value is None:
                serialized_results[name] = None
                continue
            if hasattr(value, "to_dict"):
                serialized_results[name] = value.to_dict()
                continue
            if isinstance(value, dict):
                serialized_results[name] = value
                continue
            serialized_results[name] = str(value)

        return {
            "repo": {
                "path": str(self.repo.path),
                "name": self.repo.name,
                "org": self.repo.org,
                "branch": self.repo.branch,
                "remote_url": self.repo.remote_url,
                "last_commit_date": self.repo.last_commit_date.isoformat() if self.repo.last_commit_date else None,
            },
            "results": serialized_results,
            "error": self.error,
        }


class GitScanner:
    """Scans Git repositories and generates reports."""
    
    def __init__(
        self,
        root_dir: Path,
        output_dir: Path,
        since: Optional[datetime] = None,
        recursive: bool = True,
        jobs: int = 4,
    ):
        """Initialize the scanner.
        
        Args:
            root_dir: Root directory to scan for Git repositories
            output_dir: Directory to save reports
            since: Only include repositories with changes since this date
            recursive: Whether to scan recursively
            jobs: Number of parallel jobs to use
        """
        self.root_dir = Path(root_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.since = since or (datetime.now() - timedelta(days=7))
        self.recursive = recursive
        self.jobs = jobs
        self.console = Console()
        self.report_generator = GitReportGenerator()
    
    def find_git_repos(self) -> List[GitRepo]:
        """Find all Git repositories in the root directory."""
        repos: List[GitRepo] = []
        
        if not self.root_dir.exists():
            self.console.print(f"[red]Error: Directory not found: {self.root_dir}")
            return repos
        
        self.console.print(f"[bold]Scanning for Git repositories in {self.root_dir}...")
        
        # Find all .git directories
        git_dirs = []
        for root, dirs, _ in os.walk(self.root_dir):
            if ".git" in dirs:
                git_dirs.append(Path(root))
                if not self.recursive:
                    dirs[:] = []  # Don't recurse further
        
        # Create GitRepo objects
        for git_dir in git_dirs:
            try:
                # Determine organization and repo name from path
                rel_path = git_dir.relative_to(self.root_dir)
                parts = list(rel_path.parts)

                if not parts or parts == ["."]:
                    # Root directory itself is a git repo
                    org = ""
                    repo_name = git_dir.name
                elif len(parts) == 1:
                    org = ""
                    repo_name = parts[0]
                else:
                    org = parts[0]
                    repo_name = parts[-1]
                
                repo = GitRepo(path=git_dir, name=repo_name, org=org)
                
                # Skip if no recent changes and since is specified
                if self.since and not repo.has_recent_changes(self.since):
                    continue
                    
                repos.append(repo)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Failed to process {git_dir}: {e}")
        
        return repos
    
    def scan_repo(self, repo: GitRepo) -> ScanResult:
        """Scan a single repository and return the results."""
        result = ScanResult(repo=repo)
        
        try:
            # Analyze changes first if since date is specified
            if self.since:
                self.console.print(f"  📈 Analyzing changes since {self.since.strftime('%Y-%m-%d')}...")
                analyzer = GitChangeAnalyzer(repo.path)
                result.change_summary = analyzer.analyze_changes(self.since)
                
                # Generate changelog
                changelog_path = self.output_dir / repo.org / repo.name / "changelog.md"
                changelog_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Try git-cliff first, fallback to summary
                if not analyzer.generate_changelog_with_git_cliff(self.since, changelog_path):
                    self.console.print("  [yellow]Using fallback changelog generation...[/]")
                    summary_text = analyzer.generate_summary_report(result.change_summary)
                    with open(changelog_path, 'w') as f:
                        f.write(f"# Changelog\n\nGenerated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(summary_text)
                
                self.console.print(f"  📝 Changelog saved to {changelog_path}")
            
            # Import checkers dynamically to avoid circular imports
            from weekly.checkers import (
                StyleChecker,
                CodeQualityChecker,
                DependenciesChecker,
                DocumentationChecker,
                TestChecker,
                CIChecker,
            )

            project = Project(repo.path)
            
            checkers = [
                StyleChecker(),
                CodeQualityChecker(),
                DependenciesChecker(),
                DocumentationChecker(),
                TestChecker(),
                CIChecker(),
            ]
            
            # Run all checkers
            for checker in checkers:
                try:
                    if isinstance(checker, StyleChecker):
                        check_result = checker.check(repo.path)
                    else:
                        check_result = checker.check(project)
                    result.results[checker.name] = check_result
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Checker {checker.name} failed for {repo.path}: {e}")
            
            # Generate report for this repository
            self._generate_repo_report(repo, result)
            
        except Exception as e:
            result.error = str(e)
            self.console.print(f"[red]Error scanning {repo.path}: {e}")
        
        return result
    
    def scan_all(self) -> List[ScanResult]:
        """Scan all repositories and generate reports."""
        repos = self.find_git_repos()
        
        if not repos:
            self.console.print("[yellow]No Git repositories found.")
            return []
        
        self.console.print(f"[green]Found {len(repos)} repositories to scan.")
        
        results: List[ScanResult] = []
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Scan repositories in parallel
        with ThreadPoolExecutor(max_workers=self.jobs) as executor:
            futures = {executor.submit(self.scan_repo, repo): repo for repo in repos}
            
            with Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("Scanning repositories...", total=len(futures))
                
                for future in as_completed(futures):
                    repo = futures[future]
                    try:
                        result = future.result()
                        try:
                            # Try to access attributes that might cause the error
                            _ = result.repo
                            _ = result.results
                            _ = result.error
                            results.append(result)
                        except Exception as e:
                            self.console.print(f"[red]Error processing result for {repo.path}: {e}")
                            import traceback
                            traceback.print_exc()
                    except Exception as e:
                        self.console.print(f"[red]Error scanning {repo.path}: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    progress.update(task, advance=1, description=f"Scanned {repo.name}")
        
        # Generate summary report
        self._generate_summary_report(results)
        
        return results
    
    def _generate_repo_report(self, repo: GitRepo, result: ScanResult) -> Path:
        """Generate a report for a single repository.
        
        Args:
            repo: The Git repository
            result: Scan results for the repository
            
        Returns:
            Path to the generated report
        """
        # Create output directory
        output_dir = self.output_dir / (repo.org or '') / repo.name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify directory was created and is writable
        if not output_dir.exists() or not os.access(output_dir, os.W_OK):
            raise OSError(f"Cannot write to output directory: {output_dir}")
            
        # Generate report filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"{timestamp}.html"
        report_path = output_dir / report_filename
        
        # Prepare repository info
        has_errors = result.error is not None
        for check_result in result.results.values():
            if check_result is None:
                continue
            if has_errors:
                break
            if isinstance(check_result, CoreCheckResult):
                if (check_result.status or "").lower() != "success":
                    has_errors = True
                    break
            elif hasattr(check_result, "is_ok") and not check_result.is_ok:
                has_errors = True
                break
        
        repo_info = RepoInfo(
            name=repo.name,
            org=repo.org,
            path=str(repo.path),
            branch=repo.branch,
            remote_url=repo.remote_url,
            last_commit_date=repo.last_commit_date.isoformat() if repo.last_commit_date else None,
            has_errors=has_errors
        )
        
        # Convert check results to the format expected by GitReportGenerator
        check_results: Dict[str, ReportCheckResult] = {}
        for name, check_result in result.results.items():
            if check_result is None:
                continue

            if isinstance(check_result, CoreCheckResult):
                status = (check_result.status or "").lower()
                is_ok = status == "success"
                if status == "error":
                    severity = "high"
                elif status == "warning":
                    severity = "medium"
                else:
                    severity = "low"

                # Pass metadata directly, don't wrap in another dict
                check_results[name] = ReportCheckResult(
                    name=name,
                    description="",
                    is_ok=is_ok,
                    message=check_result.title,
                    details=check_result.details,
                    next_steps=list(check_result.suggestions or []),
                    severity=severity,
                    metadata=check_result.metadata  # Pass metadata directly
                )
                continue

            # Fallback for any other checker result interface
            check_results[name] = ReportCheckResult(
                name=name,
                description=getattr(check_result, 'description', ''),
                is_ok=getattr(check_result, 'is_ok', False),
                message=getattr(check_result, 'message', ''),
                details=getattr(check_result, 'details', None),
                next_steps=getattr(check_result, 'next_steps', []),
                severity="high" if not getattr(check_result, 'is_ok', True) else "low",
                metadata=getattr(check_result, 'metadata', None)
            )
        
        # Add changelog information if available
        if result.change_summary:
            analyzer = GitChangeAnalyzer(repo.path)
            changelog_info = analyzer.generate_summary_report(result.change_summary)
            
            # Add as a special check result
            check_results["changelog"] = ReportCheckResult(
                name="changelog",
                description="Recent changes and commits",
                is_ok=True,
                message=f"Found {len(result.change_summary.commits)} commits since {self.since.strftime('%Y-%m-%d')}",
                details=changelog_info,
                next_steps=[
                    f"View full changelog: {output_dir}/changelog.md",
                    "Review recent commits for potential issues"
                ],
                severity="info",
                metadata={
                    "total_commits": len(result.change_summary.commits),
                    "files_changed": result.change_summary.total_files,
                    "additions": result.change_summary.total_additions,
                    "deletions": result.change_summary.total_deletions,
                    "commit_types": result.change_summary.commit_types
                }
            )
        
        # Generate the report
        GitReportGenerator.generate_html_report(
            results=check_results,
            repo_info=repo_info,
            output_path=report_path,
            title=f"Weekly Report - {repo.org}/{repo.name}"
        )
        
        # Create a symlink to the latest report
        latest_link = output_dir / "latest.html"
        
        # Remove existing symlink if it exists
        if latest_link.exists() or latest_link.is_symlink():
            try:
                latest_link.unlink()
                self.console.print(f"[yellow]Removed existing symlink: {latest_link}")
            except OSError as e:
                self.console.print(f"[yellow]Warning: Could not remove existing latest.html: {e}")
        
        # Create new symlink
        try:
            # Use absolute path for the target to avoid any relative path issues
            target_path = report_path.absolute()
            latest_link.symlink_to(target_path)
            self.console.print(f"[green]Created symlink: {latest_link} -> {target_path}")
        except OSError as e:
            self.console.print(f"[yellow]Warning: Could not create latest.html symlink: {e}")
            import traceback
            traceback.print_exc()
            
        return report_path
    
    def _generate_summary_report(self, results: List[ScanResult]) -> Path:
        """Generate a summary report for all repositories.
        
        Args:
            results: List of scan results
            
        Returns:
            Path to the generated summary report
        """
        if not results:
            return None
            
        summary_path = self.output_dir / "summary.html"
        
        # Prepare repository data for the summary
        repos_data: List[Dict[str, Any]] = []
        for result in results:
            has_errors = result.error is not None
            if not has_errors:
                for check in result.results.values():
                    if check is None:
                        continue
                    if isinstance(check, CoreCheckResult):
                        if (check.status or "").lower() != "success":
                            has_errors = True
                            break
                    elif hasattr(check, "is_ok") and not check.is_ok:
                        has_errors = True
                        break

            # Generate the relative path to the repository's latest report
            rel_report_path = Path(result.repo.org) / result.repo.name / "latest.html"

            repos_data.append({
                "name": result.repo.name,
                "org": result.repo.org,
                "path": str(result.repo.path),
                "branch": result.repo.branch,
                "has_errors": has_errors,
                "last_commit": result.repo.last_commit_date.strftime("%Y-%m-%d %H:%M") if result.repo.last_commit_date else "Unknown",
                "report_path": str(rel_report_path),
                "remote_url": result.repo.remote_url,
            })

        # Sort repos by organization and name
        repos_data.sort(key=lambda x: (x.get("org", "").lower(), x.get("name", "").lower()))

        GitReportGenerator.generate_summary_report(
            repos=repos_data,
            output_path=summary_path,
            title="Weekly Scan Summary",
            scan_date=datetime.now().strftime("%Y-%m-%d"),
            since_date=self.since.strftime("%Y-%m-%d") if self.since else None,
        )

        return summary_path
