# TODO

## High Priority

- [x] Unify checker interface: make all checkers accept `Project` (and update `StyleChecker` accordingly)
- [x] Remove the dual `CheckResult` models (core vs git_report) or provide a clear adapter layer/module
- [x] Add CI workflow for tests + lint + typecheck (GitHub Actions), aligned with `Makefile`
- [x] Add a real docs build pipeline (Sphinx or MkDocs) under `docs/` (currently only markdown)

## Medium Priority

- [ ] Improve `GitScanner` robustness:
  - [ ] Optional `--since` parsing should support more formats consistently
  - [x] Reduce broad `except Exception` blocks; keep actionable error messages
  - [ ] Add integration tests for `scan` command report generation
- [x] Improve `DependenciesChecker`:
  - [x] Parse `setup.py` via AST (avoid naive parsing)
  - [ ] Detect unpinned dependencies more reliably (handle extras/markers)
  - [ ] Optional: integrate vulnerability scanning (pip-audit) if available
- [ ] Improve `TestChecker`:
  - [x] Parse coverage percentage from `coverage.xml` when present
  - [ ] Distinguish between “no tests” vs “tests exist but not discovered”
- [x] Add `pre-commit` config to enforce formatting/lint on commits

## Low Priority

- [ ] Add more checkers (security, packaging, release readiness)
- [ ] Add HTML templates via a real templating engine (Jinja2) for Git reports
- [ ] Replace ad-hoc rich console printing in checkers with a structured logger
- [ ] Add benchmarks for scanning many repositories
