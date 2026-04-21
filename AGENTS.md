# Waywarden repo guidance

## Purpose
Waywarden is the core harness. It is not a one-off EA app, not a coding-only runtime, not a Home Assistant-only runtime, and not a giant autonomous agent OS.

The repo should stay:
- Python-first
- API-first
- profile-driven
- multi-instance capable
- adapter-boundary clean
- testable

## Architecture guardrails
- Keep the harness core small.
- Put provider-specific behavior behind interfaces.
- Do not leak provider types into the domain layer.
- Do not let channel adapters own business logic.
- Do not collapse memory and knowledge into one subsystem.
- Do not hardwire the runtime to a specific UI.
- Prefer shared root-level assets plus profile filtering over duplicated profile-specific copies.
- Keep policy explicit and preset-driven.
- Keep token discipline visible in code, config, contracts, and tests.

## Profile direction
The same core should support at least these profiles:
- `ea`
- `coding`
- `home`

The same deployment should support multiple named instances side by side, for example:
- `marc-ea`
- `lisa-ea`
- `coding-main`
- `ha-main`

## Repo map
- `src/waywarden/` — core application code
- `tests/` — unit, integration, and contract tests
- `profiles/` — profile descriptors and overlays
- `assets/` — shared tools, prompts, commands, routines, teams, policies, widgets, themes, and related assets
- `config/` — typed application config and later provider/profile config
- `infra/` — sidecars and local infra support
- `docs/architecture/` — ADRs and architecture decisions
- `docs/research/` — outside references and ideas worth borrowing selectively
- `docs/contributing.md` — Definition of Done, label taxonomy, milestones, phase map
- Active execution tracking lives in GitHub Issues, not in repo markdown

## Tooling and commands
- Python: `3.13`
- Package/dev runner: `uv`
- Lint: `make lint`
- Format: `make format`
- Tests: `make test`
- Local app: `make run`
- Dev server: `make dev`
- Sidecar Postgres: `make db-up`
- Migrations: `make migrate`

## Working rules
- For Codex runs, default to `rtk` for any shell command likely to emit more than a small screen of output; only use raw commands when unfiltered output is necessary.
- Token discipline matters. When using shell commands that can produce large or noisy output, prefer `rtk` wrappers so Codex sees compressed results instead of raw terminal noise.
- Default to `rtk` for noisy commands such as `git status`, `git diff`, `git log`, `rg`, `find`, `ls -R`, test runners, coverage, build logs, and similar high-volume terminal output.
- Use normal commands only when raw/unfiltered output is specifically required for correctness or debugging.
- If choosing between a built-in tool path and a noisy shell path, prefer the path that keeps context smallest while still preserving correctness.
- `src/waywarden` is strictly typed. Tests are checked but lightly relaxed.
- For third-party dependencies lacking stubs (e.g. `honcho`), do not use blanket ignores. Instead, add targeted `[[tool.mypy.overrides]]` in `pyproject.toml` with `ignore_missing_imports = true` mapped only to that module.
- Use existing patterns before introducing new ones.
- Make small, surgical changes unless the task explicitly requires broader refactoring.
- Update tests with every behavioral change.
- Run the most relevant checks first, then broader validation before claiming completion.
- Do not mark work complete while tests, lint, or typing are knowingly broken in touched areas.
- Prefer typed, explicit code over clever implicit behavior.
- Keep placeholders honest: never return fake-success responses for unimplemented behavior.
- Keep issue scope tight unless a directly related defect must be fixed to make the requested work actually correct.

## GitHub workflow
- Treat GitHub Issues as the source of truth for active work.
- Do not re-introduce a markdown backlog under `docs/`. Planning conventions live in `docs/contributing.md`; execution lives in GitHub Issues.
- When working from an epic, complete the next actionable child issue in order unless issue text clearly allows parallelism.
- After implementation, adversarially review your own work, fix defects, then update the issue with notes grounded in what actually changed.
- **Always use the `gh` CLI for all GitHub operations** (reading issues, posting comments, closing issues, listing PRs, etc.). Never launch a browser or browser subagent for GitHub tasks. The `gh` CLI is authenticated and is the correct tool.

## Git / issue execution policy

Issue completion is defined as: merged into `main`, verified on `main`, issue closed, branch deleted. Branch-only completion does not count as complete.

When working a GitHub issue, follow this workflow unless the user explicitly instructs otherwise:

1. Create a new issue branch from the current `main`.
   - Branch naming:
     - `issue-<number>-<short-slug>`
   - Example:
     - `issue-40-p2-5-run-event`

2. Implement the issue work on that branch only.
   - Do not commit issue work directly to `main`.
   - Keep scope tightly limited to the issue and its explicit acceptance criteria.

3. Validate on the issue branch before pushing.
   - Run targeted tests first.
   - Run broader relevant validation if reasonably fast.
   - Run lint/type checks required by the repo or issue.

4. Push the branch to origin.

5. Merge the branch back into `main` only after validation passes.
   - Prefer a clean merge/rebase path that preserves an understandable history.
   - Do not leave the work completed only on the branch.

6. Verify that `main` contains the final intended commit/content.
   - Confirm the merged result on `main`, not just on the feature branch.
   - If the merge rewrites history or changes commit SHA, verify the content, not just the original SHA string.

7. Close the GitHub issue only after the work is confirmed on `main`.

8. Delete the remote and local issue branch after successful merge and verification unless the user explicitly asks to keep it.

### Required completion evidence
When reporting completion of an issue, include:
- issue branch name
- final commit SHA on branch
- final commit SHA on `main` after merge, if different
- validation commands run
- explicit confirmation that `main` contains the completed work
- confirmation that the issue was closed
- confirmation that the branch was deleted, or note that it was intentionally retained

### Prohibited behaviors
- Do not work issue-to-completion only on a branch and then close the issue without merging.
- Do not commit directly to `main` unless the user explicitly says to do so.
- Do not assume the issue is complete until `main` is verified.
- Do not leave both branch and `main` with divergent implementations of the same issue.

## Skills and long procedures
Use repo-local skills for repeatable workflows instead of bloating this file with long procedures. This file should stay focused on durable repo facts, hard constraints, and always-on working agreements.
