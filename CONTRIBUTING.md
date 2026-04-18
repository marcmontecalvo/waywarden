# Contributing to Waywarden

Thank you for your interest in contributing to Waywarden!

## Local Development Setup

Waywarden uses `uv` for dependency management and Python execution.

1. Ensure Python 3.13 is installed.
2. Ensure you have `uv` installed.
3. Clone the repo and install dependencies:
   ```bash
   uv sync
   ```

## Development Commands

We use a `Makefile` for standard workflows. Before pushing, ensure all checks pass:

- **Format code**: `make format`
- **Lint code**: `make lint`
- **Run tests**: `make test`
- **Check typing**: `make typecheck` (if applicable, part of lint)
- **Secret Scan**: `make secret-scan`

### Quality Gates

- **Tests**: We enforce a minimum 80% branch coverage threshold (`--cov-fail-under=80`).
- **Formatting**: `ruff` is used for linting and formatting.
- **Typing**: `mypy` is run with strict scope for the `waywarden.*` tree.
- **Security**: Secret scanning via `gitleaks` is enforced in CI.

## Submitting Changes

1. Create a branch for your work.
2. Implement your changes.
3. Keep the scope tight to the issue.
4. Update tests and assure `make test` runs without error.
5. Create a Pull Request against `main`.
