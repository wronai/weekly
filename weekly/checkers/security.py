"""
Security checker for Weekly - checks for common security issues and secrets.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.project import Project
from ..core.report import CheckResult
from .base import BaseChecker


class SecurityChecker(BaseChecker):
    """Checker for security issues and secrets."""

    @property
    def name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Checks for secrets, insecure functions, and common security misconfigurations"

    def check(self, project: Project) -> Optional[CheckResult]:
        """
        Check the project for security issues.

        Args:
            project: The project to check

        Returns:
            CheckResult with security-related findings
        """
        if not project.is_python_project:
            return None

        # 1. Detect potential secrets
        secrets = self._detect_secrets(project)

        # 2. Detect insecure functions
        insecure_funcs = self._detect_insecure_functions(project)

        # 3. Detect insecure files (e.g., .env committed)
        insecure_files = self._detect_insecure_files(project)

        findings = []
        suggestions = []
        metadata: Dict[str, Any] = {
            "secrets_found": len(secrets),
            "insecure_functions_found": len(insecure_funcs),
            "insecure_files_found": len(insecure_files),
            "issues_data": {},
        }

        if secrets:
            findings.append(
                f"Found {len(secrets)} potential secrets/keys in the codebase."
            )
            suggestions.append(
                "Use environment variables or a secret manager (e.g., AWS Secrets Manager, Vault) instead of hardcoding secrets."
            )
            metadata["issues_data"]["secrets"] = secrets

        if insecure_funcs:
            findings.append(
                f"Found {len(insecure_funcs)} usages of potentially insecure functions (e.g., eval, exec)."
            )
            suggestions.append(
                "Avoid using eval(), exec(), and os.system(). Use safer alternatives like ast.literal_eval() or the subprocess module."
            )
            metadata["issues_data"]["insecure_functions"] = insecure_funcs

        if insecure_files:
            findings.append(
                f"Found {len(insecure_files)} sensitive files that should not be committed (e.g., .env)."
            )
            suggestions.append(
                "Add sensitive files like .env to your .gitignore and remove them from the repository history."
            )
            metadata["issues_data"]["insecure_files"] = insecure_files

        if not findings:
            return CheckResult(
                checker_name=self.name,
                title="Security check passed",
                status="success",
                details="No common security issues or hardcoded secrets were detected.",
                suggestions=["Regularly run security scanners like bandit or safety"],
                metadata=metadata,
            )

        return CheckResult(
            checker_name=self.name,
            title="Potential Security Issues Found",
            status="warning" if len(findings) < 3 else "error",
            details="\n".join(findings),
            suggestions=list(set(suggestions)),
            metadata=metadata,
        )

    def _detect_secrets(self, project: Project) -> List[Dict[str, Any]]:
        """Detect potential secrets using regex patterns."""
        secret_patterns = {
            "Generic API Key": r"(?:key|api|token|secret|password|passwd|auth)[-_]?(?:key|api|token|secret|password|passwd|auth)?\s*[:=]\s*['\"]([a-zA-Z0-9]{16,})['\"]",
            "AWS Access Key": r"AKIA[0-9A-Z]{16}",
            "AWS Secret Key": r"['\"]?[a-zA-Z0-9/+=]{40}['\"]?",
            "GitHub Personal Access Token": r"ghp_[a-zA-Z0-9]{36}",
            "Slack Token": r"xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}",
            "Private Key": r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----",
        }

        found_secrets = []
        for py_file in project.path.glob("**/*.py"):
            file_rel_path = str(py_file.relative_to(project.path))
            if any(
                part in file_rel_path
                for part in ["venv", ".tox", "build", "tests", "checkers/security.py"]
            ):
                continue

            content = project.get_file_content(file_rel_path)
            if not content:
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                for name, pattern in secret_patterns.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        found_secrets.append(
                            {
                                "file": str(py_file.relative_to(project.path)),
                                "line": line_num,
                                "type": name,
                                "code": "SEC100",
                                "message": f"Potential {name} detected",
                            }
                        )
        return found_secrets

    def _detect_insecure_functions(self, project: Project) -> List[Dict[str, Any]]:
        """Detect usage of insecure Python functions."""
        insecure_patterns = {
            "eval()": r"\beval\s*\(",
            "exec()": r"\bexec\s*\(",
            "os.system()": r"os\.system\s*\(",
            "pickle.loads()": r"pickle\.loads\s*\(",
            "yaml.load()": r"yaml\.load\s*\([^,)]*\)",  # without Loader=...
        }

        found_funcs = []
        for py_file in project.path.glob("**/*.py"):
            file_rel_path = str(py_file.relative_to(project.path))
            if any(
                part in file_rel_path
                for part in ["venv", ".tox", "build", "checkers/security.py"]
            ):
                continue

            content = project.get_file_content(file_rel_path)
            if not content:
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                for name, pattern in insecure_patterns.items():
                    if re.search(pattern, line):
                        found_funcs.append(
                            {
                                "file": str(py_file.relative_to(project.path)),
                                "line": line_num,
                                "type": name,
                                "code": "SEC200",
                                "message": f"Usage of insecure function {name} detected",
                            }
                        )
        return found_funcs

    def _detect_insecure_files(self, project: Project) -> List[Dict[str, Any]]:
        """Detect sensitive files committed to Git."""
        sensitive_files = [
            ".env",
            "*.pem",
            "*.key",
            "id_rsa",
            "secrets.yaml",
            "secrets.json",
            ".pypirc",
        ]

        found_files = []
        for pattern in sensitive_files:
            for sensitive_file in project.path.glob(f"**/{pattern}"):
                if any(
                    part in str(sensitive_file) for part in ["venv", ".tox", "build"]
                ):
                    continue

                found_files.append(
                    {
                        "file": str(sensitive_file.relative_to(project.path)),
                        "line": 0,
                        "type": "Sensitive File",
                        "code": "SEC300",
                        "message": f"Sensitive file '{sensitive_file.name}' committed to repository",
                    }
                )
        return found_files
