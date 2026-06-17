# Project Config

This file is the canonical, human-readable source of truth for repo structure, guideline loading, review triggers, and repo-level command rules.

If another repo document conflicts with this file, follow this file.

## Purpose

- Use this file as rule, not background reading.
- Humans read it to understand expected agent behavior.
- Agents read it to decide which guidelines, reviews, and commands apply.

## Repo Structure

- `demo/`: Example usage and integration scripts.
- `dist/`: Build artifacts (e.g., Python wheels).
- `docs/`: User-facing documentation and functional specs.
- `src/`: Main source code for the `postgres-task-queue` package.
- `tests/`: Test suite.
- `work/`: aifact artifacts (stories, guidelines, ADRs, ideas).
- `work/guidelines/`: Technical guidelines for development.
- `work/stories/`: Story state and implementation details.
- `work/adr/`: Architecture Decision Records (currently empty).
- `work/ideas/`: Idea capture and exploration.

## Output Rules

- TODO: Define concise response and formatting rules for agents.

## Domain Rules

- **Documentation-Driven Development**:
  - Guideline: `work/guidelines/documentation-driven-development.md`
  - File patterns: `docs/specs/**/*.md`
  - Keywords: spec, functional requirement, edge case, failure mode, example

## Technology Rules

- **Python**: Primary language for the `postgres-task-queue` package.
  - Tools: `uv`, `ruff`, `pytest`, `ty` (type checking).
  - File patterns: `src/**/*.py`, `tests/**/*.py`, `pyproject.toml`

- **PostgreSQL**: Task queue storage backend.
  - File patterns: `pgmq.sql`, `docker-compose.yaml`, `docker-entrypoint-initdb.d/`

## Review Rules

- TODO: Define review types, trigger keywords, and linked guideline files.

## Loading Rules

### Always Load

- `work/guidelines/documentation-driven-development.md` (functional specs).

### Analysis

- Agents must load guidelines matching the **domain** (e.g., `docs/specs/**/*.md` for Documentation-Driven Development).

### Implementation

- Agents must load guidelines matching the **affected files** (e.g., Python files for Python guidelines).

### Validation

- Agents must load guidelines and review checks matching the **story requirements** (e.g., spec validation for Documentation-Driven Development).

## Command Rules

- **Validation**: `make validate` (runs linting, type checking, and tests).
- **Linting**: `make lint` (ruff check + format).
- **Type Checking**: `make ty` (type checking with `ty`).
- **Testing**: `make test` (pytest).

## Agent Usage Rule

- Read this file first when you need repo structure, guideline loading rules, review triggers, or repo-level command rules.
- Load only the guideline files that match the current task.
- Do not invent rules outside this file, `AGENTS.md`, and the loaded guideline files.
