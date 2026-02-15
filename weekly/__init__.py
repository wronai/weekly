"""
Weekly - A tool for analyzing project quality and suggesting next steps.
"""

__version__: str = "0.0.0"

try:
    from importlib.metadata import version

    __version__ = version("weekly")
except Exception:
    pass

from pathlib import Path
from typing import Any, Dict, List, Optional

# Import checkers
from .checkers.base import BaseChecker
from .checkers.ci_cd import CIChecker
from .checkers.code_quality import CodeQualityChecker
from .checkers.dependencies import DependenciesChecker
from .checkers.docs import DocumentationChecker
from .checkers.packaging import PackagingChecker
from .checkers.release_readiness import ReleaseReadinessChecker
from .checkers.security import SecurityChecker
from .checkers.style import StyleChecker
from .checkers.testing import TestChecker

# Import and expose CLI
from .cli import main
from .core.analyzer import analyze_project

# Import core components
from .core.project import Project
from .core.report import CheckResult, Report
from .git_report import GitReportGenerator, RepoInfo

# Import Git scanner and report generator
from .git_scanner import GitRepo, GitScanner, ScanResult

__all__ = [
    # Core functionality
    "analyze_project",
    "Project",
    "Report",
    "main",  # Export main as cli
    "CheckResult",
    # Checkers
    "BaseChecker",
    "TestChecker",
    "DocumentationChecker",
    "CIChecker",
    "DependenciesChecker",
    "CodeQualityChecker",
    "StyleChecker",
    "SecurityChecker",
    "PackagingChecker",
    "ReleaseReadinessChecker",
    # Git scanning
    "GitRepo",
    "GitScanner",
    "ScanResult",
    "GitReportGenerator",
    "RepoInfo",
]
