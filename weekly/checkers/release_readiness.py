"""
Release readiness checker for Weekly - checks if the project is ready for a release.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.project import Project
from ..core.report import CheckResult
from .base import BaseChecker


class ReleaseReadinessChecker(BaseChecker):
    """Checker for release readiness."""

    @property
    def name(self) -> str:
        return "release_readiness"

    @property
    def description(self) -> str:
        return "Checks for version consistency, changelog updates, and release artifacts"

    def check(self, project: Project) -> Optional[CheckResult]:
        """
        Check if the project is ready for a release.

        Args:
            project: The project to check

        Returns:
            CheckResult with release readiness findings
        """
        if not project.is_python_project:
            return None

        # 1. Check version consistency
        version_info = self._check_version_consistency(project)

        # 2. Check if changelog is updated for the current version
        changelog_info = self._check_changelog_status(project, version_info["version"])

        # 3. Check for distribution files (dist/*)
        dist_info = self._check_dist_files(project)

        findings = []
        suggestions = []
        status = "success"

        if not version_info["consistent"]:
            findings.append("Version inconsistency detected between project files.")
            suggestions.append("Ensure the version string is the same in pyproject.toml, setup.py, and __init__.py.")
            status = "warning"

        if not changelog_info["updated"]:
            findings.append(f"Changelog might not be updated for version {version_info['version']}.")
            suggestions.append(f"Update CHANGELOG.md with changes for version {version_info['version']}.")
            if status == "success":
                status = "suggestion"

        if not dist_info["exists"]:
            findings.append("No distribution files found in dist/ directory.")
            suggestions.append("Run 'poetry build' or 'python -m build' to generate distribution artifacts.")
            if status == "success":
                status = "suggestion"

        details = [
            f"**Current Version:** {version_info['version'] or 'Unknown'}",
            f"**Version Consistent:** {'Yes' if version_info['consistent'] else 'No'}",
            f"**Changelog Updated:** {'Yes' if changelog_info['updated'] else 'No'}",
            f"**Dist Artifacts:** {'Found' if dist_info['exists'] else 'Missing'}",
        ]

        return CheckResult(
            checker_name=self.name,
            title="Release Readiness Analysis",
            status=status,
            details="\n".join(details) + "\n\n" + "\n".join(findings),
            suggestions=suggestions,
            metadata={**version_info, **changelog_info, **dist_info}
        )

    def _check_version_consistency(self, project: Project) -> Dict[str, Any]:
        """Check for version consistency across common files."""
        versions = {}
        
        # 1. pyproject.toml
        if project.pyproject:
            if "tool" in project.pyproject and "poetry" in project.pyproject["tool"]:
                versions["pyproject.toml"] = project.pyproject["tool"]["poetry"].get("version")
            elif "project" in project.pyproject:
                versions["pyproject.toml"] = project.pyproject["project"].get("version")

        # 2. setup.py
        if project.setup_py:
            import re
            match = re.search(r"version=['\"]([^'\"]+)['\"]", project.setup_py)
            if match:
                versions["setup.py"] = match.group(1)

        # 3. __init__.py
        init_file = project.path / project.path.name / "__init__.py"
        if not init_file.exists():
            # Try to find any __init__.py with __version__
            for f in project.path.glob("**/__init__.py"):
                content = project.get_file_content(str(f.relative_to(project.path)))
                if content and "__version__" in content:
                    import re
                    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
                    if match:
                        versions[str(f.relative_to(project.path))] = match.group(1)
                        break

        unique_versions = set(v for v in versions.values() if v)
        main_version = next(iter(unique_versions)) if unique_versions else None
        
        return {
            "version": main_version,
            "consistent": len(unique_versions) <= 1,
            "versions_found": versions
        }

    def _check_changelog_status(self, project: Project, version: Optional[str]) -> Dict[str, Any]:
        """Check if the changelog contains the current version."""
        if not version:
            return {"updated": False, "found_in_changelog": False}

        changelog_files = ["CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG"]
        for filename in changelog_files:
            content = project.get_file_content(filename)
            if content:
                if version in content:
                    return {"updated": True, "found_in_changelog": True, "file": filename}
        
        return {"updated": False, "found_in_changelog": False}

    def _check_dist_files(self, project: Project) -> Dict[str, Any]:
        """Check for existence of distribution artifacts."""
        dist_dir = project.path / "dist"
        exists = dist_dir.exists() and any(dist_dir.iterdir())
        files = [f.name for f in dist_dir.iterdir()] if exists else []
        
        return {
            "exists": exists,
            "files": files
        }
