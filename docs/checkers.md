# Checkers

Weekly checkers produce a `CheckResult` that is later rendered by the reporter.

## Available checkers

- **Testing** (`weekly/checkers/testing.py`)
  - Detects presence of tests and test configuration.
  - Can detect existence of coverage files.

- **Documentation** (`weekly/checkers/docs.py`)
  - Validates presence of core docs files like README, LICENSE, CHANGELOG.

- **CI/CD** (`weekly/checkers/ci_cd.py`)
  - Detects common CI configs and (basic) deployment hints.

- **Dependencies** (`weekly/checkers/dependencies.py`)
  - Extracts dependencies from multiple sources and flags unpinned specs.

- **Code Quality** (`weekly/checkers/code_quality.py`)
  - Detects formatters/linters/type checkers and looks for common issues.

- **Security** (`weekly/checkers/security.py`)
  - Detects hardcoded secrets (API keys, tokens, private keys).
  - Flags usage of insecure functions like `eval()`, `exec()`, or `os.system()`.
  - Checks for sensitive files committed to the repository (e.g., `.env`).

- **Packaging** (`weekly/checkers/packaging.py`)
  - Checks for PEP 517/518 compliance (build-system in `pyproject.toml`).
  - Validates essential distribution metadata (name, version, authors, etc.).
  - Verifies README linkage in package configuration.

- **Style** (`weekly/checkers/style.py`)
  - Runs external tools (Black/isort/flake8/mypy) and collects issues.

## Conventions

- Status values should be consistent across checkers (`success`, `warning`, `error`, `suggestion`).
- Checkers should prefer analyzing via `Project` when possible to keep a single interface.
