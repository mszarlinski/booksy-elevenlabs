# VBOOK-01 — Bootstrap the Python project

**Priority:** P0
**Goal:** Learn the modern Python development ecosystem before building application logic.

## Description

Create the initial repository and establish the development workflow for the voice-booking backend.

## TODO

* [ ] Install and configure Python 3.12+
* [ ] Create the project using `uv`
* [ ] Understand `pyproject.toml`
* [ ] Add runtime dependencies:

  * FastAPI
  * Uvicorn
  * Pydantic
  * SQLAlchemy
  * asyncpg
* [ ] Add development dependencies:

  * pytest
  * pytest-asyncio
  * Ruff
  * mypy
  * httpx
* [ ] Configure Ruff formatting and linting
* [ ] Configure mypy
* [ ] Create Python package structure
* [ ] Add `.env` configuration using Pydantic Settings
* [ ] Create a basic `/health` endpoint
* [ ] Add Makefile or equivalent developer commands
* [ ] Write a short README explaining how to run the project

## Learning objectives

Understand:

* Python packages and modules
* virtual environments
* dependency management
* `pyproject.toml`
* type hints
* Python linting/formatting ecosystem

## Acceptance criteria

Running:

```bash
uv run fastapi dev
```

starts the application and:

```http
GET /health
```

returns HTTP 200.
