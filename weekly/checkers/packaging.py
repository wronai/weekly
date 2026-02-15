"""
Packaging checker for Weekly - checks for PEP 517/518 compliance and metadata.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.project import Project
from ..core.report import CheckResult
from .base import BaseChecker


class PackagingChecker(BaseChecker):
    """Checker for project packaging and distribution metadata."""

    @property
    def name(self) -> str:
        return "packaging"

    @property
    def description(self) -> str:
        return "Checks for PEP 517/518 compliance, build system configuration, and package metadata"

    def check(self, project: Project) -> Optional[CheckResult]:
        """
        Check the project's packaging setup.

        Args:
            project: The project to check

        Returns:
            CheckResult with packaging-related findings
        """
        if not project.is_python_project:
            return None

        # 1. Check for modern build system (PEP 517/518)
        build_system = self._check_build_system(project)

        # 2. Check for essential metadata
        metadata = self._check_metadata(project)

        # 3. Check for distribution configuration
        dist_config = self._check_dist_config(project)

        findings = []
        suggestions = []
        status = "success"

        if not build_system["pep517"]:
            findings.append("Project does not follow PEP 517/518 (missing [build-system] in pyproject.toml).")
            suggestions.append("Add a [build-system] section to your pyproject.toml to specify your build backend.")
            status = "warning"

        if metadata["missing"]:
            findings.append(f"Missing essential package metadata: {', '.join(metadata['missing'])}.")
            suggestions.append("Ensure your project configuration (pyproject.toml or setup.py) includes name, version, description, authors, and license.")
            status = "warning"

        if not dist_config["has_readme_in_config"]:
            findings.append("README not explicitly linked in packaging configuration.")
            suggestions.append("Ensure your README file is specified in the metadata so it appears on PyPI.")
            if status == "success":
                status = "suggestion"

        if not findings:
            return CheckResult(
                checker_name=self.name,
                title="Packaging setup looks good",
                status="success",
                details="Project follows modern packaging standards and has complete metadata.",
                suggestions=["Consider using a build tool like Poetry, Flit, or Hatch"],
                metadata={**build_system, **metadata, **dist_config}
            )

        return CheckResult(
            checker_name=self.name,
            title="Packaging Improvements Suggested",
            status=status,
            details="\n".join(findings),
            suggestions=list(set(suggestions)),
            metadata={**build_system, **metadata, **dist_config}
        )

    def _check_build_system(self, project: Project) -> Dict[str, Any]:
        """Check for PEP 517/518 compliance."""
        has_build_system = False
        backend = "unknown"
        
        if project.pyproject and "build-system" in project.pyproject:
            has_build_system = True
            backend = project.pyproject["build-system"].get("build-backend", "unknown")

        return {
            "pep517": has_build_system,
            "build_backend": backend,
            "has_pyproject": project.pyproject is not None
        }

    def _check_metadata(self, project: Project) -> Dict[str, Any]:
        """Check for essential package metadata."""
        missing = []
        found = {}
        
        # Check pyproject.toml (Poetry or PEP 621)
        if project.pyproject:
            if "tool" in project.pyproject and "poetry" in project.pyproject["tool"]:
                poetry = project.pyproject["tool"]["poetry"]
                found["name"] = "name" in poetry
                found["version"] = "version" in poetry
                found["description"] = "description" in poetry
                found["authors"] = "authors" in poetry
                found["license"] = "license" in poetry
            elif "project" in project.pyproject:
                p = project.pyproject["project"]
                found["name"] = "name" in p
                found["version"] = "version" in p
                found["description"] = "description" in p
                found["authors"] = "authors" in p
                found["license"] = "license" in p

        # Fallback to setup.py check if still missing (simplified)
        if not found.get("name") and project.setup_py:
            content = project.setup_py.lower()
            found["name"] = "name=" in content
            found["version"] = "version=" in content
            found["description"] = "description=" in content
            found["license"] = "license=" in content

        essential = ["name", "version", "description", "authors", "license"]
        for field in essential:
            if not found.get(field):
                missing.append(field)

        return {"missing": missing, "metadata_found": found}

    def _check_dist_config(self, project: Project) -> Dict[str, Any]:
        """Check for distribution-specific configuration."""
        has_readme = False
        
        if project.pyproject:
            if "tool" in project.pyproject and "poetry" in project.pyproject["tool"]:
                has_readme = "readme" in project.pyproject["tool"]["poetry"]
            elif "project" in project.pyproject:
                has_readme = "readme" in project.pyproject["project"]
        
        if not has_readme and project.setup_py:
            has_readme = "long_description" in project.setup_py.lower()

        return {"has_readme_in_config": has_readme}
