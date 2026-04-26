---
name: work-next-issue-in-given-epic
description: Resolve the next actionable child issue from a GitHub EPIC, implement it fully, prove the acceptance criteria with issue-scoped tests, adversarially review/fix it, then commit, push, merge to main, verify main, update GitHub, close the issue, and close the epic when appropriate.
---

# work-next-issue-in-given-epic

Use this skill when the user gives a GitHub EPIC issue URL and wants fully autonomous execution of the **next open actionable child issue**.

This skill is the authoritative repo-local workflow. Do not call a global skill resolver. Open and follow this file directly.

## Inputs

- GitHub EPIC issue URL or EPIC issue number
- Current repo working tree
- Repo issue bodies/comments
- Linked specs / ADRs / docs needed to understand the selected child issue

## Mandatory workflow

1. Resolve the active EPIC and identify the next actionable child issue.
2. Read the child issue body, comments, linked specs, and any related acceptance criteria.
3. Run repo-intelligence preflight (`.agents/skills/work-next-issue-in-given-epic/assets/repo-intelligence-checklist.md`). Use CodeGraph if available and worthwhile; otherwise fall back cleanly.
4. Sync/inspect `main`, create a fresh issue branch from current `main`, and record the baseline.
5. Run the mandatory baseline checks before editing code.
6. Identify the issue’s exact acceptance criteria before changing code.
7. Add or update the tests that prove those acceptance criteria.
8. Run the relevant new/changed tests and confirm they fail for the right reason when applicable.
9. Implement the selected issue with tight scope on that branch.
10. Run validation on that branch.
11. Perform adversarial review.
12. Correct defects and re-run validation until the work genuinely passes.
13. Run the mandatory pre-commit gate.
14. Commit the code changes on the issue branch.
15. Push the issue branch and verify the push succeeded.
16. Merge the issue branch into `main`.
17. Verify `main` contains the final intended result and run the required post-merge checks.
18. Post completion notes to the child issue and the EPIC.
19. Close the child issue.
20. If that child issue completed the EPIC, update and close the EPIC too.
21. Delete the issue branch unless the user explicitly asked to keep it.
22. Return the required output format.

## Baseline and “preexisting failure” rule

A failure may be called preexisting **only** when it was captured before issue edits began.

Immediately after creating the issue branch from current `main`, and before modifying files, run:

```bash
git status --short
make lint
make test
```

If the repo has an explicit typecheck command or make target, run that too.

Rules:

- If baseline checks pass, every later lint/test/typecheck failure is considered introduced by this issue until proven otherwise and must be fixed before commit.
- If baseline checks fail, stop and report `FAIL` unless the selected issue explicitly exists to fix that failure or the user explicitly told you to continue.
- If you did not run the baseline checks before editing, you may not claim a later failure is preexisting. Treat it as yours and fix it or revert your change.
- Do not hand-wave failures as unrelated. Prove it with a clean baseline, a diff audit, and targeted reruns.
- If a failure appears after your edits, fix it before moving on, even if it looks unrelated, unless you can demonstrate from the baseline log that it already existed.

## Testing and acceptance-proof rule

Tests are built with each issue, not deferred to a later cleanup pass.

### Required execution model for every issue

1. identify the acceptance criteria from the issue body, linked specs, ADRs, and comments
2. add or update the tests that prove those acceptance criteria
3. run the relevant new/changed tests and confirm they fail for the right reason when applicable
4. implement the code with scope kept tight to the issue
5. run `make format`, `make lint`, and `make test` until green; run typecheck too when the repo exposes it
6. perform adversarial review and correct any defects found
7. rerun the relevant validation after every material code/test/doc change
8. merge only when the issue’s behavior is actually proven

### Completion rule

An issue cannot be marked complete unless the tests proving its acceptance criteria were added or updated in the same issue workflow.

Overall coverage does not substitute for issue-level proof.

### An issue is not done if

- code exists but the acceptance criteria are not covered by tests
- tests were postponed to a later cleanup pass
- CI, lint, typecheck, format, or test failures remain on the issue branch or on `main`
- integration behavior promised by the issue is untested
- the implementation passes shallow tests but does not prove the stated acceptance criteria
- adversarial review found defects that were not corrected and revalidated
- the issue claims behavior that is not tied to explicit tests
- `make format`, `make lint`, and `make test` were not run after the final material change and before commit
- the work was committed or pushed while validation was failing

### For infra/setup/schema/migration issues where pure test-first is awkward

- the issue must still leave behind the validating tests in the same issue/branch
- write the proving tests as early as practical, even if some scaffolding must exist first
- no issue may rely on a future issue just to prove its own acceptance criteria unless that dependency is explicitly written in the issue body
- “this will be tested later” is not an acceptable completion rationale

### Required proof in the final output

For each acceptance criterion, state:

- which test(s) prove it
- whether it passed
- any limitation or follow-up, if one truly remains

If the acceptance criteria cannot be mapped to tests, the run is not complete.

### Coverage policy

- overall coverage is a secondary signal, not the primary proof of correctness
- rising coverage is good, but it does not excuse missing issue-level tests
- do not use aggregate coverage to justify closing an issue with unproven acceptance criteria
- prefer truthful issue-level validation over inflated aggregate coverage

### Default operating model

Red → green → format → lint → test → review → validate → commit → push → merge → verify main.

“Implement now, test later” is not acceptable.

## Mandatory validation gates

### Baseline gate before edits

Run immediately after branch creation and before editing:

```bash
git status --short
make lint
make test
```

Run typecheck if the repo exposes it, for example `make typecheck`, `uv run mypy ...`, or the documented project command.

### Development validation

During implementation:

- run targeted tests as soon as tests are added or changed
- run targeted tests after every material implementation change
- run broader tests when shared contracts, persistence, schemas, provider protocols, CI, or integration behavior are touched
- fix failures before expanding scope or moving on

### Mandatory pre-commit gate

Before **every** commit, run exactly this sequence from the issue branch:

```bash
git status --short
make format
make lint
make test
```

Also run typecheck when the repo exposes it.

Rules:

- If `make format` changes files, inspect the diff, include legitimate formatting changes, and rerun `make lint` and `make test` after formatting.
- If any command fails, do not commit. Fix the failure, cleanup partial artifacts, and rerun the full pre-commit gate.
- If generated files, temporary files, caches, logs, or partial test artifacts were created by failed runs, remove or intentionally ignore them before commit.
- Commit only after the working tree contains the intended issue changes and the full gate passes.

### Mandatory post-merge gate

After merging to `main`, verify from `main`:

```bash
git checkout main
git pull --ff-only
make lint
make test
```

Run typecheck when available. If post-merge validation fails, the issue is not complete; fix on a new issue branch or the same branch if still available, then rerun the full workflow.

## Non-negotiable rules

- Do not stop until tests pass.
- Do not claim success while the working tree is dirty unless the remaining dirt is deliberate, explained, and outside the selected issue.
- Do not claim success unless required repo changes are committed.
- Do not claim success unless required remote updates are pushed.
- Do not claim success unless the work is merged into `main` and verified on `main`.
- Do not claim success unless GitHub issue notes/checklists/state reflect the finished work.
- Do not leave the child issue open if the work is complete.
- Do not leave the EPIC open if this was the last required item and the EPIC's definition of done is satisfied.
- Do not use fake-success placeholders, TODO-only implementations, or hand-wavy closeout comments.
- Keep scope tight to the selected issue unless a directly related defect blocks truthful completion.
- Do not close the child issue while the work exists only on a feature branch.
- Do not leave divergent branch/main implementations for the same issue.
- Do not use overall coverage as a substitute for proving acceptance criteria.
- Do not mark an issue complete if the tests proving its acceptance criteria were not added or updated in the same issue workflow.
- Do not blame “preexisting errors” unless the exact failure was captured by the baseline gate before edits began.
- Be aggressive about token discipline during repo inspection and validation. Prefer `rtk`-wrapped shell commands for noisy output (git diffs/status, ripgrep/find scans, test runs, coverage, build logs) unless raw output is required to resolve the issue truthfully.

## Mandatory GitHub issue workflow

For every issue worked with this skill, follow this exact sequence unless the user explicitly overrides it:

1. Create a fresh issue branch from current `main`.
2. Run and record the baseline gate before edits.
3. Read the issue/spec/docs/comments and identify acceptance criteria.
4. Add/update the tests that prove the acceptance criteria.
5. Implement the issue on that branch.
6. Run required validation on that branch.
7. Run adversarial review and fix defects.
8. Run the full pre-commit gate.
9. Commit.
10. Push the branch and verify push success.
11. Merge branch into `main`.
12. Verify `main` contains the final intended result.
13. Run the post-merge gate on `main`.
14. Add completion notes to the child issue and EPIC.
15. Close the issue.
16. Delete the branch.

## Issue selection rules

When choosing the next actionable child issue from an EPIC:

- prefer the first open child issue whose dependencies are satisfied
- respect explicit `Depends on: #N` lines in issue bodies
- respect label/state signals such as `blocked`, `design`, or `spike`
- do not skip to a later issue unless the earlier one is truly blocked or not executable
- if an issue is mislabeled but clearly executable based on the body/spec/dependencies, call that out in the final output and proceed carefully
- if no child issue is actionable, return `FAIL` with the exact blocker

## Canonical GitHub CLI reads

Use `gh` CLI only for GitHub operations.

Start with the minimum stable issue read:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels
```

If the issue has comments that may contain relevant information, add `comments` to the JSON fields.

If more metadata is specifically needed, only use fields confirmed by `gh`:

- assignees
- author
- body
- closed
- closedAt
- comments
- createdAt
- id
- labels
- milestone
- number
- projectCards
- reactionGroups
- state
- title
- updatedAt
- url

Never request unsupported fields such as:

- reactions
- subIssues

If a `gh` command fails because of an invalid JSON field:

1. stop retrying variants blindly
2. fall back immediately to:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels
```

3. continue from there

## Repo intelligence preflight

Follow `.agents/skills/work-next-issue-in-given-epic/assets/repo-intelligence-checklist.md`.

Minimum expectations:

1. inspect repo size, language mix, and task shape
2. use CodeGraph or another repo-intelligence index if available and useful
3. if indexing is unavailable, unsupported, or not worth the overhead, fall back to normal repo exploration
4. never trust index-only results blindly; open and verify every touched file directly before editing
5. do not block the task on repo indexing

Optional CodeGraph guidance:

- use CodeGraph opportunistically, not as a hard dependency
- prefer it for architectural tracing, impact analysis, and cross-file refactors
- skip or de-prioritize it for tiny repos or highly localized changes
- confirm touched files manually before editing
- do not let indexing failure stop the run

## Branch naming

Use:

- `issue-<issue-number>-<short-slug>`

## Validation expectations

Validation must be issue-appropriate and honest.

At minimum, run:

- relevant targeted tests
- `make format` before commit
- `make lint` before commit and after merge
- `make test` before commit and after merge
- typecheck when the repo exposes it
- any repo-specific validation explicitly required by the issue/spec/CI

Rules:

- run the smallest truthful validation set first, then widen as needed
- if an issue changes shared contracts, persistence, schemas, or CI-facing behavior, broaden validation accordingly
- if adversarial review finds a defect, fix it and re-run the relevant validation
- do not report `PASS` if required validation was skipped
- do not rely on stale earlier test runs after material code changes
- do not commit if lint/tests/typecheck are red

## Before closing the issue, confirm all of the following

- baseline gate was run before edits, or any failure is treated as introduced by the issue
- pre-commit gate passed after the final material change
- branch was pushed
- merge to `main` succeeded
- `main` contains the final code
- post-merge gate passed on `main`
- acceptance criteria are tied to tests
- issue is ready to close
- branch is deleted or intentionally retained with explanation

## Never do this

- never close the issue while the work exists only on a feature branch
- never report completion based only on branch state
- never leave divergent branch/main implementations for the same issue without explicitly calling that out and resolving it
- never treat aggregate coverage as sufficient proof that an issue is done
- never defer missing acceptance tests to a later cleanup pass unless the issue explicitly says so
- never claim “preexisting failure” without baseline evidence captured before edits
- never commit after a failed lint/test/typecheck run until the failure is corrected and validation rerun

## Git / GitHub closeout requirements

Follow `.agents/skills/work-next-issue-in-given-epic/assets/git-and-github-closeout.md` exactly.

Minimum required closeout:

- review `git status`, `git diff`, current branch, and remotes before finalizing
- create or confirm the correct issue branch from current `main`
- run baseline gate before edits
- run pre-commit gate before every commit
- commit with a clear, issue-linked message
- push the issue branch and verify the push succeeded
- merge the issue branch into `main`
- verify `main` contains the intended final content
- run post-merge validation on `main`
- add a substantive completion note on the child issue
- update the EPIC checklist / progress note
- close the child issue
- if the EPIC is now done, close the EPIC
- delete the issue branch unless intentionally retained

If the environment or permissions prevent push/merge/closeout, the run is **not PASS**. Output **FAIL** and state the exact external blocker.

## Child issue note requirements

Post a substantive completion note that includes:

- what was implemented
- key files changed
- baseline validation commands and results
- tests/validation run after implementation
- pre-commit validation commands and results
- post-merge validation commands and results
- adversarial review findings
- corrections made after review
- issue branch name
- final issue-branch commit sha
- final main commit sha if different
- explicit confirmation that `main` now contains the completed work

## Failure conditions

The run must be marked `FAIL` if any of these are true:

- baseline was skipped and a later failure is claimed as preexisting
- tests/validation required by the issue do not pass
- `make format`, `make lint`, or `make test` was skipped before commit
- typecheck was skipped when the repo exposes it
- acceptance criteria were not actually proven by tests
- code/docs changed but were not committed
- push did not happen or failed
- merge to `main` did not happen or failed
- post-merge validation on `main` did not pass
- `main` was not verified after merge
- child issue was not updated/closed
- EPIC was not updated correctly
- EPIC should have been closed but was left open
- the work exists only on a feature branch at the end of the run

## Output contract

Use `.agents/skills/work-next-issue-in-given-epic/assets/output-format.md` exactly.

## Required output additions for acceptance-proof discipline

Within the required output format:

- in `## VALIDATION RUN`, include the exact commands used for baseline, targeted validation, pre-commit gate, and post-merge gate
- in `## ACCEPTANCE STATUS`, map each acceptance criterion to one or more proving tests and mark `PASS` or `FAIL`
- if a criterion is only partially proven, mark it `FAIL`
- if a criterion has no proving test, mark it `FAIL`
- do not return `PASS` in `## RESULT` unless every acceptance criterion is tied to passing proof

## Result contract

Return `PASS` only if all of the following are true:

- acceptance criteria are met
- acceptance criteria are actually proven by tests added or updated in the same issue workflow
- baseline gate was run before edits or no preexisting-failure claim was made
- tests/validation pass
- `make format`, `make lint`, and `make test` passed before every commit
- typecheck passed when available
- issues found in adversarial review were corrected
- required code changes are committed
- required remote updates are pushed
- work was merged into `main`
- post-merge validation passed on `main`
- `main` was verified to contain the final implementation
- child issue notes/state are updated correctly
- EPIC notes/checklist/state are updated correctly
- branch was deleted or intentionally retained with explanation

Otherwise return `FAIL`.
