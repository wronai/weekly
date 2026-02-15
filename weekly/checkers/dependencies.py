"""
Dependencies checker for Weekly - checks project dependencies and their health.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.project import Project
from ..core.report import CheckResult
from .base import BaseChecker


class DependenciesChecker(BaseChecker):
    """Checker for project dependencies."""

    @property
    def name(self) -> str:
        return "dependencies"

    @property
    def description(self) -> str:
        return (
            "Checks project dependencies, their versions, and potential vulnerabilities"
        )

    def check(self, project: Project) -> Optional[CheckResult]:
        """
        Check the project's dependencies.

        Args:
            project: The project to check

        Returns:
            CheckResult with dependencies-related findings
        """
        if not project.is_python_project:
            return None

        # Get dependencies from different sources
        deps = self._get_dependencies(project)

        if not deps["dependencies"] and not deps["dev_dependencies"]:
            return CheckResult(
                checker_name=self.name,
                title="No dependencies specified",
                status="warning",
                details=(
                    "No dependencies were found in pyproject.toml, setup.py, or requirements.txt.\n"
                    "This might be correct if your project has no external dependencies."
                ),
                suggestions=[
                    "Add your project's dependencies to pyproject.toml or requirements.txt",
                    "If you're using setup.py, declare dependencies in setup_requires or install_requires",
                ],
            )

        # Check for unpinned dependencies
        unpinned = self._find_unpinned_dependencies(deps)

        # Check for vulnerabilities via pip-audit
        vulnerabilities = self._run_pip_audit(project)

        if vulnerabilities:
            return CheckResult(
                checker_name=self.name,
                title=f"Found {len(vulnerabilities)} security vulnerabilities",
                status="error",
                details=(
                    f"Vulnerability scan found {len(vulnerabilities)} issues:\n"
                    + "\n".join([f"- {v}" for v in vulnerabilities])
                ),
                suggestions=[
                    "Run 'pip-audit' manually to see detailed vulnerability reports",
                    "Update the vulnerable packages to their latest secure versions",
                    "Consider using a tool like Snyk or GitHub Dependency Graph for continuous monitoring",
                ],
                metadata={"vulnerabilities": vulnerabilities},
            )

        if unpinned:
            return CheckResult(
                checker_name=self.name,
                title=f"Found {len(unpinned)} unpinned dependencies",
                status="warning",
                details=(
                    f"The following dependencies are not pinned to a specific version: {', '.join(unpinned)}.\n"
                    "Unpinned dependencies can lead to build inconsistencies and unexpected behavior."
                ),
                suggestions=[
                    f"Pin {dep} to a specific version (e.g., {dep}==1.2.3)"
                    for dep in unpinned
                ]
                + [
                    "Consider using a tool like pip-tools or poetry for dependency management"
                ],
            )

        # Check for outdated dependencies (simulated - in a real implementation, this would check PyPI)
        outdated = self._find_outdated_dependencies(deps)

        if outdated:
            return CheckResult(
                checker_name=self.name,
                title=f"Found {len(outdated)} potentially outdated dependencies",
                status="suggestion",
                details=(
                    f"The following dependencies might be outdated: {', '.join(outdated)}.\n"
                    "Consider updating to the latest stable versions."
                ),
                suggestions=[
                    f"Check if there's a newer version of {dep} available"
                    for dep in outdated
                ]
                + ["Run 'pip list --outdated' to check for outdated packages"],
            )

        # If we get here, dependencies look good
        return CheckResult(
            checker_name=self.name,
            title="Dependencies look good",
            status="success",
            details=(
                f"Found {len(deps['dependencies'])} runtime and {len(deps['dev_dependencies'])} development dependencies.\n"
                "All dependencies appear to be properly pinned."
            ),
            suggestions=[
                "Regularly update your dependencies to receive security fixes",
                "Consider using Dependabot or Renovate to automate dependency updates",
            ],
        )

    def _get_dependencies(self, project: Project) -> Dict[str, List[Tuple[str, str]]]:
        """
        Extract dependencies from various project files.

        Returns:
            Dict with 'dependencies' and 'dev_dependencies' lists of (name, constraint) tuples
        """
        result: Dict[str, List[Tuple[str, str]]] = {"dependencies": [], "dev_dependencies": []}

        # Check pyproject.toml (PEP 621 or Poetry)
        if project.pyproject:
            # Poetry
            if "tool" in project.pyproject and "poetry" in project.pyproject["tool"]:
                poetry = project.pyproject["tool"]["poetry"]

                # Main dependencies
                if "dependencies" in poetry:
                    for name, spec in poetry["dependencies"].items():
                        if name.lower() != "python":
                            constraint = (
                                self._normalize_constraint(spec)
                                if isinstance(spec, str)
                                else "any"
                            )
                            result["dependencies"].append((name, constraint))

                # Dev dependencies
                if "dev-dependencies" in poetry:
                    for name, spec in poetry["dev-dependencies"].items():
                        constraint = (
                            self._normalize_constraint(spec)
                            if isinstance(spec, str)
                            else "any"
                        )
                        result["dev_dependencies"].append((name, constraint))

                # Extras
                if "extras" in poetry:
                    for extra_name, deps in poetry["extras"].items():
                        for dep in deps:
                            name, _, constraint = self._parse_dep_spec(dep)
                            result["dependencies"].append((name, constraint or "any"))

            # PEP 621
            elif "project" in project.pyproject:
                project_config = project.pyproject["project"]

                # Dependencies
                if "dependencies" in project_config:
                    for dep in project_config["dependencies"]:
                        name, _, constraint = self._parse_dep_spec(dep)
                        result["dependencies"].append((name, constraint or "any"))

                # Optional dependencies
                if "optional-dependencies" in project_config:
                    for extra_name, deps in project_config[
                        "optional-dependencies"
                    ].items():
                        for dep in deps:
                            name, _, constraint = self._parse_dep_spec(dep)
                            result["dependencies"].append((name, constraint or "any"))

        # Check setup.py via AST parsing
        setup_py_path = project.path / "setup.py"
        if setup_py_path.exists():
            try:
                import ast
                tree = ast.parse(setup_py_path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "setup":
                        for keyword in node.keywords:
                            if keyword.arg == "install_requires" and isinstance(keyword.value, ast.List):
                                for elt in keyword.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        name, _, constraint = self._parse_dep_spec(elt.value)
                                        result["dependencies"].append((name, constraint or "any"))
                            elif keyword.arg == "extras_require" and isinstance(keyword.value, ast.Dict):
                                for val in keyword.value.values:
                                    if isinstance(val, ast.List):
                                        for elt in val.elts:
                                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                                name, _, constraint = self._parse_dep_spec(elt.value)
                                                result["dependencies"].append((name, constraint or "any"))
            except Exception:
                # Fallback to naive parsing if AST fails
                content = project.setup_py.lower()
                if "install_requires" in content:
                    pass

        # Check requirements.txt
        if project.requirements_txt:
            for dep in project.requirements_txt:
                name, _, constraint = self._parse_dep_spec(dep)
                if name and name.lower() not in ["-e", "--editable"]:
                    result["dependencies"].append((name, constraint or "any"))

        return result

    def _parse_dep_spec(self, spec: str) -> Tuple[str, str, str]:
        """Parse a dependency specification into (name, version_spec, extras)."""
        # Remove whitespace and comments
        spec = spec.split("#")[0].strip()
        if not spec:
            return "", "", ""

        # Handle environment markers (PEP 508)
        marker = ""
        if ";" in spec:
            spec, marker = spec.split(";", 1)
            spec = spec.strip()
            marker = marker.strip()

        # Handle extras
        extras = ""
        if "[" in spec and "]" in spec:
            start = spec.find("[")
            end = spec.find("]")
            extras = spec[start + 1 : end]
            spec = spec[:start] + spec[end + 1 :]

        # Split on comparison operators
        for op in ["==", ">=", "<=", ">", "<", "~=", "!="]:
            if op in spec:
                name, version = spec.split(op, 1)
                return name.strip(), op, version.strip()

        # No version specified
        return spec.strip(), "", ""

    def _normalize_constraint(self, constraint: str) -> str:
        """Normalize version constraints for comparison."""
        # This is a simplified version - a real implementation would need to handle all cases
        constraint = constraint.strip()

        if not constraint or constraint == "*":
            return "any"

        # Remove spaces around comparison operators
        for op in ["==", ">=", "<=", ">", "<", "~=", "!="]:
            if op in constraint:
                name, version = constraint.split(op, 1)
                return f"{name.strip()}{op}{version.strip()}"

        return constraint

    def _find_unpinned_dependencies(
        self, deps: Dict[str, List[Tuple[str, str]]]
    ) -> List[str]:
        """Find dependencies that don't have version constraints."""
        unpinned: List[Tuple[str, str]] = []

        for dep_type in ["dependencies", "dev_dependencies"]:
            for name, constraint in deps[dep_type]:
                if constraint == "any" and name not in [d[0] for d in unpinned]:
                    unpinned.append((name, constraint))

        # Sort by name for consistent output
        return sorted([dep[0] for dep in unpinned])

    def _find_outdated_dependencies(
        self, deps: Dict[str, List[Tuple[str, str]]]
    ) -> List[str]:
        """Find potentially outdated dependencies."""
        # In a real implementation, this would check PyPI or a vulnerability database
        # For now, we'll just return an empty list
        return []

    def _run_pip_audit(self, project: Project) -> List[str]:
        """Run pip-audit on the project to find vulnerabilities."""
        import subprocess

        vulnerabilities = []
        try:
            # Try to run pip-audit on the project path
            # We look for requirements.txt or pyproject.toml
            cmd = ["pip-audit", "--format", "json"]

            # If it's a poetry project, we might want to use poetry export first or just audit the path
            # pip-audit can audit pyproject.toml if it's PEP 621, or we can audit requirements.txt
            
            # Simple approach: audit the directory if pip-audit is installed
            result = subprocess.run(
                cmd + [str(project.path)],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0 and result.stdout:
                try:
                    import json
                    data = json.loads(result.stdout)
                    # pip-audit JSON format: {"dependencies": [{"name": "...", "version": "...", "vulnerabilities": [...]}]}
                    if "dependencies" in data:
                        for dep in data["dependencies"]:
                            if dep.get("vulnerabilities"):
                                for vuln in dep["vulnerabilities"]:
                                    vulnerabilities.append(f"{dep['name']} {dep['version']}: {vuln.get('id', 'Unknown Vuln')}")
                except json.JSONDecodeError:
                    pass
        except FileNotFoundError:
            # pip-audit not installed
            pass
        except Exception:
            pass
            
        return vulnerabilities
