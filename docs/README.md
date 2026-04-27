---
type: index
title: "Documentation Map and Navigation"
status: Active
date: 2026-04-27
source_url: null
source_type: index
priority: directly-relevant
tags: [navigation, structure, metadata]
relates_to_adrs: null
---

# Docs map

This docs tree is split by **intent**, not by age.

**Key reference**: All documents must include [YAML frontmatter](./FRONTMATTER-SPEC.md)
with metadata for discovery and linking.

## Operator guides

### `setup/`

Getting a working local instance running.

- [quickstart.md](setup/quickstart.md) — clone → install → migrate → run → smoke check
- [providers.md](setup/providers.md) — Honcho, LLM-Wiki, Anthropic, tracing, policy
- [ea-instance.md](setup/ea-instance.md) — configure marc-ea, add lisa-ea, profile selection

### `usage/`

Day-to-day operation and API reference.

- [ea-operator-guide.md](usage/ea-operator-guide.md) — what EA does today, task/approval/delegation flows
- [api-smoke-tests.md](usage/api-smoke-tests.md) — curl commands for every endpoint

## Architecture

### `architecture/`

Canonical architecture decisions (ADRs) and durable design rules. If a note
changes how Waywarden should be built, it ends up here.

## Other folders

- `orchestration/` — milestone catalog documentation
- `prompts/` — prompt assets for coding agents and bootstrap flows
- `research/` — external products, repos, UX references (pattern notes only)
- `references/` — external inspiration
- `specs/` — runtime protocol specs (RT-001, RT-002), skill contracts

## Folder rules

1. Put **durable decisions** in `architecture/`.
2. Put **fast-moving external observations** in `research/`.
3. Put **operator setup and usage** in `setup/` and `usage/`.
4. Put **execution prompts** in `prompts/`.
5. If a research note changes the actual design, write or update an ADR.
6. **All documents must include YAML frontmatter** (type, title, status, date).
   See [FRONTMATTER-SPEC.md](./FRONTMATTER-SPEC.md) for the standard.

## Local development

Install the dev toolchain and git hooks:

```bash
make bootstrap
uv run pre-commit install
```

Run the full hook set manually:

```bash
uv run pre-commit run --all-files
```

Configured hooks:
- `ruff format`
- `ruff check --fix`
- `mypy` on staged Python files in `src/` and `tests/`
- `trailing-whitespace`
- `end-of-file-fixer`
