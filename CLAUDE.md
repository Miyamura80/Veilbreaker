# AGENTS.md

You are **not allowed under any circumstances** to read into the folder `agents_no_read/`.

## Project Overview

Super-opinionated Python stack for fast development. Python `>=3.12` is required. The project uses `uv` for dependency management and task execution.

## Common Commands

```bash
# Onboarding & setup
make onboard
make all

# Testing
make test
make test_fast
make test_flaky
make test_slow
make test_nondeterministic

# Code quality
make fmt
make ruff
make vulture
make ty
make lint_links
make ci

# Dependencies / execution
uv sync
uv add <pkg>
uv run python <file>
uv run pytest path/to/test.py
```

## Architecture

- `common/`: global configuration via pydantic-settings and YAML files
- `src/`: application code
- `src/server/`: credential telemetry server MVP
- `src/utils/`: shared utilities
- `utils/llm/`: DSPy and Langfuse LLM integration helpers
- `tests/`: pytest suites and shared test template
- `init/`: initialization scripts

## Code Style

- `snake_case` for functions, files, and directories
- `CamelCase` for classes
- `UPPERCASE` for constants
- 4-space indentation
- double quotes
- prefer built-in collection types like `list`, `dict`, and `tuple`
- do not use `datetime.utcnow()`; use `datetime.now(timezone.utc)` or equivalent

## Configuration Pattern

```python
from common import global_config

global_config.example_parent.example_child
global_config.default_llm.default_model
global_config.OPENAI_API_KEY
```

## Testing Pattern

```python
from tests.test_template import TestTemplate


class TestMyFeature(TestTemplate):
    def test_something(self):
        assert self.config is not None
```

## Logging

```python
from loguru import logger as log
from src.utils.logging_config import setup_logging

setup_logging()
log.info("message")
```

## Git Workflow

- `main` is protected; do not push directly to it
- use pull requests
- squash and merge
- never force-push
- always run `make ci` before committing

## Docs Note

Docs under `docs/content/` are auto-translated by the Jules Translation Sync workflow. Do not manually translate localized doc files; update the English source instead.
