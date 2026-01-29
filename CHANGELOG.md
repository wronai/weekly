## [0.1.37] - 2026-01-29

### Summary

feat(goal): deep code analysis engine with 7 supporting modules

### Test

- update test_change.py

### Config

- config: update goal.yaml


## [0.1.37] - 2026-01-29

### Summary

feat(goal): deep code analysis engine with 7 supporting modules

### Test

- update test_change.py

### Config

- config: update goal.yaml


## [0.1.36] - 2026-01-29

### Summary

feat(core): add cli, validation, api

### Test

- update tests/debug_parse_mypy.py
- update tests/test_analyzer.py
- update tests/test_cli.py
- update tests/test_reporter.py
- update tests/test_style_checker.py

### Other

- update weekly/__init__.py
- update weekly/checkers/__init__.py
- update weekly/checkers/base.py
- update weekly/checkers/ci_cd.py
- update weekly/checkers/code_quality.py
- update weekly/checkers/dependencies.py
- update weekly/checkers/docs.py
- update weekly/checkers/style.py
- update weekly/checkers/testing.py
- update weekly/cli.py
- ... and 9 more


## [0.1.35] - 2026-01-29

### Summary

docs(docs): better documentation

### Docs

- docs: update llm_usage_guide.md

### Config

- config: update goal.yaml


## [0.1.34] - 2026-01-29

### Summary

docs(docs): add markdown output

### Changes

- build: update Makefile
- docs: update README
- docs: update llm_usage_guide.md
- update requirements.txt
- update weekly/git_change_analyzer.py
- update weekly/git_scanner.py

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added `TODO.md`
- Added basic documentation pages in `docs/` (`index.md`, `development.md`, `architecture.md`, `checkers.md`)

### Changed
- `weekly.__version__` is now derived from package metadata at runtime (with a safe fallback)

### Fixed
- Added missing `markdown` runtime dependency to Poetry configuration
- Removed duplicated `ReportGenerator.save_reports` implementation
- Replaced deprecated `datetime.utcnow()` usage with timezone-aware UTC timestamps
- Cleaned up `GitScanner` summary report generation (removed dead code, fixed logic) and adapted checker execution to use `Project` where applicable

## [0.1.3] - 2025-06-07

### Added
- Project quality analyzer with modular checkers system
- Support for analyzing test coverage and configuration
- Documentation checker for README, LICENSE, and other project files
- CI/CD configuration detection
- Dependency analysis for Python projects
- Code quality checks (formatting, linting, type checking)
- Command-line interface with multiple output formats (text, JSON, Markdown)
- Programmatic API for integration with other tools
- Comprehensive test suite
- Documentation and contribution guidelines

### Changed
- Switched from setuptools to Poetry for dependency management
- Updated project structure to support modular checkers
- Improved error handling and reporting
- Enhanced documentation with examples and usage guides
- Updated README with badges and detailed installation instructions

### Fixed
- Various bug fixes and improvements

## [0.1.0] - 2023-01-01

### Added
- Initial project setup with core functionality
- Git repository analysis capabilities
- Basic report generation in JSON, Markdown, and HTML formats
- Command-line interface for basic usage
