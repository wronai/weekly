"""
Testing checker for Weekly - checks for test configuration and coverage.
"""
from pathlib import Path
from typing import Optional

from ..core.project import Project
from ..core.report import CheckResult
from .base import BaseChecker


class TestChecker(BaseChecker):
    """Checker for testing configuration and coverage."""

    @property
    def name(self) -> str:
        return "testing"

    @property
    def description(self) -> str:
        return (
            "Checks for test configuration, test coverage, and testing best practices"
        )

    def check(self, project: Project) -> Optional[CheckResult]:
        """
        Check the project's testing setup.

        Args:
            project: The project to check

        Returns:
            CheckResult with testing-related findings
        """
        if not project.is_python_project:
            return None

        has_tests = project.has_tests
        has_test_config = self._has_test_config(project)
        test_coverage = self._check_test_coverage(project)

        # Look for test files specifically
        test_files = list(project.path.glob("**/test_*.py")) + list(
            project.path.glob("**/*_test.py")
        )
        tests_discovered = len(test_files) > 0

        if not has_tests and not has_test_config:
            return CheckResult(
                checker_name=self.name,
                title="No tests or test configuration found",
                status="error",
                details=(
                    "No test files (tests/, test/) or test configuration "
                    "(pytest.ini, setup.cfg with test settings) were found."
                ),
                suggestions=[
                    "Add tests for your code in a 'tests' directory",
                    "Consider using pytest for testing (add pytest to your dev dependencies)",
                    "Add a pytest.ini or setup.cfg with test configuration",
                ],
            )

        if not tests_discovered and has_test_config:
            return CheckResult(
                checker_name=self.name,
                title="Test configuration found but no tests discovered",
                status="warning",
                details=(
                    "Testing is configured, but no test files (test_*.py or *_test.py) "
                    "were found in the project. Tests might be missing or not follow naming conventions."
                ),
                suggestions=[
                    "Ensure test files are named correctly (e.g., test_*.py)",
                    "Check if tests are in a directory excluded from scanning",
                    "Add unit tests for your core logic",
                ],
            )

        if has_tests and not has_test_config:
            return CheckResult(
                checker_name=self.name,
                title="Tests found but no test configuration",
                status="warning",
                details=(
                    "Test files were found but no explicit test configuration "
                    "(pytest.ini, setup.cfg with test settings) was detected."
                ),
                suggestions=[
                    "Add a pytest.ini or setup.cfg with test configuration",
                    "Consider adding test coverage reporting with coverage.py",
                ],
            )

        if test_coverage is not None and test_coverage < 80:  # Threshold for warning
            return CheckResult(
                checker_name=self.name,
                title=f"Low test coverage: {test_coverage}%",
                status="warning",
                details=(
                    f"Test coverage is currently at {test_coverage}%, "
                    "which is below the recommended 80% threshold."
                ),
                suggestions=[
                    "Add more test cases to improve coverage",
                    "Consider using a tool like pytest-cov to measure coverage",
                    "Add a coverage threshold to fail CI if coverage is too low",
                ],
            )

        if (
            has_tests
            and has_test_config
            and (test_coverage is None or test_coverage >= 80)
        ):
            return CheckResult(
                checker_name=self.name,
                title="Testing setup looks good",
                status="success",
                details=(
                    f"Tests and test configuration found"
                    + (f" with {test_coverage}% coverage" if test_coverage else "")
                    + "."
                ),
                suggestions=[
                    "Consider adding integration tests if you don't have them",
                    "Add end-to-end tests for critical user journeys",
                ]
                if test_coverage and test_coverage >= 90
                else [],
            )

        return None

    def _has_test_config(self, project: Project) -> bool:
        """Check if the project has test configuration."""
        # Check for common test configuration files
        test_config_files = [
            "pytest.ini",
            "tox.ini",
            "setup.cfg",
            "pyproject.toml",
            ".coveragerc",
        ]

        for config_file in test_config_files:
            if (project.path / config_file).exists():
                # Check if the file contains test-related configuration
                content = project.get_file_content(config_file)
                if content and any(
                    keyword in content.lower()
                    for keyword in ["test", "pytest", "coverage"]
                ):
                    return True

        # Check setup.py for test requirements
        setup_py = project.setup_py
        if setup_py and "test_requires" in setup_py:
            return True

        return False

    def _check_test_coverage(self, project: Project) -> Optional[float]:
        """
        Check test coverage if coverage files are present.

        Returns:
            Test coverage percentage as a float (0-100) or None if not available
        """
        # Look for coverage.xml first as it's easiest to parse
        coverage_xml = project.path / "coverage.xml"
        if coverage_xml.exists():
            try:
                import xml.etree.ElementTree as ET

                tree = ET.parse(coverage_xml)
                root = tree.getroot()
                # coverage.xml usually has line-rate attribute in the root <coverage> element
                line_rate = root.get("line-rate")
                if line_rate:
                    return round(float(line_rate) * 100, 2)
            except Exception:
                pass

        # Look for .coverage file or htmlcov/index.html
        coverage_files = [".coverage", "htmlcov/index.html"]

        for cov_file in coverage_files:
            if (project.path / cov_file).exists():
                return None

        # Check for coverage in setup.cfg or .coveragerc
        for config_file in ["setup.cfg", ".coveragerc"]:
            content = project.get_file_content(config_file)
            if content and "coverage" in content.lower():
                return None

        return None
