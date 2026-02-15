# TODO

## High Priority

- [x] Unify checker interface: make all checkers accept `Project` (and update `StyleChecker` accordingly)
- [x] Remove the dual `CheckResult` models (core vs git_report) or provide a clear adapter layer/module
- [x] Add CI workflow for tests + lint + typecheck (GitHub Actions), aligned with `Makefile`
- [x] Add a real docs build pipeline (Sphinx or MkDocs) under `docs/` (currently only markdown)

## Medium Priority

- [x] Improve `GitScanner` robustness:
  - [x] Optional `--since` parsing should support more formats consistently
  - [x] Reduce broad `except Exception` blocks; keep actionable error messages
  - [x] Add integration tests for `scan` command report generation
- [x] Improve `DependenciesChecker`:
  - [x] Parse `setup.py` via AST (avoid naive parsing)
  - [x] Detect unpinned dependencies more reliably (handle extras/markers)
  - [x] Optional: integrate vulnerability scanning (pip-audit) if available
- [x] Improve `TestChecker`:
  - [x] Parse coverage percentage from `coverage.xml` when present
  - [x] Distinguish between “no tests” vs “tests exist but not discovered”
- [x] Add `pre-commit` config to enforce formatting/lint on commits

## Low Priority

- [x] Add more checkers (security, packaging, release readiness)
- [x] Add HTML templates via a real templating engine (Jinja2) for Git reports
- [x] Replace ad-hoc rich console printing in checkers with a structured logger
- [x] Add benchmarks for scanning many repositories
