"""
Core analysis functionality for Weekly.
"""
from pathlib import Path
from typing import List

from ..checkers.ci_cd import CIChecker
from ..checkers.code_quality import CodeQualityChecker
from ..checkers.dependencies import DependenciesChecker
from ..checkers.docs import DocumentationChecker
from ..checkers.packaging import PackagingChecker
from ..checkers.release_readiness import ReleaseReadinessChecker
from ..checkers.security import SecurityChecker
from ..checkers.style import StyleChecker

# Import all checkers
from ..core.logger import get_logger
from ..checkers.testing import TestChecker
from .project import Project
from .report import CheckResult, Report

logger = get_logger(__name__)


def analyze_project(project_path: Path) -> Report:
    """
    Analyze a project and generate a report with suggested next steps.

    Args:
        project_path: Path to the project directory

    Returns:
        Report: A report containing analysis results and suggestions
    """
    project = Project(project_path)
    report = Report(project)

    # Register all available checkers
    checkers = [
        StyleChecker(),
        TestChecker(),
        DocumentationChecker(),
        CIChecker(),
        DependenciesChecker(),
        CodeQualityChecker(),
        SecurityChecker(),
        PackagingChecker(),
        ReleaseReadinessChecker(),
    ]

    # Run all checkers
    for checker in checkers:
        try:
            result = checker.check(project)
            if result:
                report.add_result(result)
        except Exception as e:
            # Log the error but continue with other checkers
            logger.error(f"Error running {checker.__class__.__name__}: {str(e)}")

    return report
