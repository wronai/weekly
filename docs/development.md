# Development

## Requirements

- Python 3.8+
- Poetry

## Setup

```bash
poetry install --with dev
```

## Running tests

```bash
poetry run pytest
```

Or via Makefile:

```bash
make test
```

## Linting / formatting

```bash
make lint
make format
make typecheck
```

## Running the CLI locally

```bash
poetry run weekly --help
poetry run weekly analyze .
poetry run weekly scan .
```
