# Architecture

Weekly has two major feature areas:

## 1) Project analysis (`weekly analyze`)

- **`weekly/core/project.py`**: representation of a project (filesystem + parsed config).
- **`weekly/core/analyzer.py`**: orchestrates running checkers over a `Project`.
- **`weekly/core/report.py`**: aggregates results and renders outputs (text/markdown/json).
- **`weekly/checkers/*`**: modular checks (tests/docs/ci/dependencies/code quality/style).

## 2) Multi-repo Git scanning (`weekly scan`)

- **`weekly/git_scanner.py`**: discovers repositories and runs checkers per repo.
- **`weekly/git_report.py`**: HTML report generation for scanned repositories.
- **`weekly/git_analyzer.py`**: commit history analysis for trend-style data.

## Known architectural friction

- Some checkers operate on `Project`, while `StyleChecker` operates on `Path`.
- There are two `CheckResult` models (core report vs git report), which requires adapters.

These are good targets for unification to simplify maintenance and reduce edge cases.
