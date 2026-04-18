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

## Dependency Updates

Waywarden uses `uv` for dependency management.

### Dependabot

We use Dependabot to monitor for dependency updates in the `pip` and `github-actions` ecosystems. Dependabot is scheduled to run weekly.

### Refreshing `uv.lock`

Because `uv` support in Dependabot is relatively new, you may occasionally need to manually refresh the lockfile if a Dependabot PR modifies `pyproject.toml` but the lock resolution needs local adjustment, or if performing a manual update:

1. Check out the PR branch locally: `gh pr checkout <PR-NUMBER>`
2. Run `uv lock --upgrade` to refresh `uv.lock`.
3. Verify tests pass: `make test`
4. Commit the updated lockfile: `git commit -am "Update uv.lock"`
5. Push changes to the branch.

### Security-Driven Exceptions

If a critical vulnerability requires immediate mitigation before the next Dependabot run:
1. Update the dependency version in `pyproject.toml` (if not deep in the tree).
2. Manually run `uv lock --upgrade-package <package_name>`.
3. Submit a PR with the updated `uv.lock`.

### Review and Merging

Lockfile refresh PRs should be reviewed carefully to ensure CI remains green. Since automated upgrades can introduce breaking changes, any test failures must be addressed by modifying our code or pinning the dependency in `pyproject.toml` before merging. 

## Submitting Changes

1. Create a branch for your work.
2. Implement your changes.
3. Keep the scope tight to the issue.
4. Update tests and assure `make test` runs without error.
5. Create a Pull Request against `main`.
