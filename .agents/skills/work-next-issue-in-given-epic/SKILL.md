---
name: work-next-issue-in-given-epic
description: Resolve the next actionable child issue from a GitHub EPIC, implement it fully, prove the acceptance criteria with issue-scoped tests, adversarially review/fix it, then commit, push, merge to main, verify main, update GitHub, close the issue, and close the epic when appropriate.
---

# work-next-issue-in-given-epic

Use this skill when the user gives you a GitHub EPIC issue URL and wants fully autonomous execution of the **next open actionable child issue**.

## Inputs

- GitHub EPIC issue URL
- Current repo working tree
- Repo issue bodies/comments
- Linked specs / ADRs / docs needed to understand the selected child issue

## Mandatory workflow

1. Resolve the active EPIC and identify the next actionable child issue.
2. Read the child issue body, comments, linked specs, and any related acceptance criteria.
3. Run repo-intelligence preflight (`.agents/skills/work-next-issue-in-given-epic/assets/repo-intelligence-checklist.md`). Use CodeGraph if available and worthwhile; otherwise fall back cleanly.
4. Create a fresh issue branch from current `main`.
5. Identify the issue’s exact acceptance criteria before changing code.
6. Add or update the tests that prove those acceptance criteria.
7. Run the relevant new/changed tests and confirm they fail for the right reason when applicable.
8. Implement the selected issue with tight scope on that branch.
9. Run validation on that branch.
10. Perform adversarial review.
11. Correct defects and re-run validation until the work genuinely passes.
12. **Commit the code changes on the issue branch.**
13. **Push the issue branch.**
14. **Merge the issue branch into `main`.**
15. **Verify `main` contains the final intended result.**
16. **Post completion notes to the child issue and the EPIC.**
17. **Close the child issue.**
18. **If that child issue completed the EPIC, update and close the EPIC too.**
19. **Delete the issue branch unless the user explicitly asked to keep it.**
20. Return the required output format.

## Testing and acceptance-proof rule

Tests are built with each issue, not deferred to a later cleanup pass.

### Required execution model for every issue

1. identify the acceptance criteria from the issue body, linked specs, ADRs, and comments
2. add or update the tests that prove those acceptance criteria
3. run the relevant new/changed tests and confirm they fail for the right reason when applicable
4. implement the code with scope kept tight to the issue
5. run lint, typecheck, and the relevant test suite until green
6. perform adversarial review and correct any defects found
7. merge only when the issue’s behavior is actually proven

### Completion rule

An issue cannot be marked complete unless the tests proving its acceptance criteria were added or updated in the same issue workflow.

Overall coverage does not substitute for issue-level proof.

### An issue is not done if

- code exists but the acceptance criteria are not covered by tests
- tests were postponed to a later “cleanup” pass
- CI, typecheck, or test failures remain on `main`
- integration behavior promised by the issue is untested
- the implementation passes shallow tests but does not prove the stated acceptance criteria
- adversarial review found defects that were not corrected and revalidated
- the issue claims behavior that is not tied to explicit tests

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

Red → green → review → merge is the default.

“Implement now, test later” is not acceptable.

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
- Be aggressive about token discipline during repo inspection and validation. Prefer `rtk`-wrapped shell commands for noisy output (git diffs/status, ripgrep/find scans, test runs, coverage, build logs) unless raw output is required to resolve the issue truthfully.

## Mandatory GitHub issue workflow

For every issue worked with this skill, follow this exact sequence unless the user explicitly overrides it:

1. Create a fresh issue branch from current `main`
2. Read the issue/spec/docs/comments and identify acceptance criteria
3. Add/update the tests that prove the acceptance criteria
4. Implement the issue on that branch
5. Run required validation on that branch
6. Push the branch
7. Merge branch into `main`
8. Verify `main` contains the final intended result
9. Close the issue
10. Delete the branch

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

### Issue read commands

Start with the minimum stable issue read:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels
```

*If the issue has comments that may contain relevant information, add `comments` to the JSON fields.*

### If more metadata is specifically needed, only use fields confirmed by gh:

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

### Never request unsupported fields such as:

- reactions
- subIssues

### If a gh command fails because of an invalid JSON field:

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

At minimum, run the checks required by the selected issue and repo policy. This commonly includes:

- relevant targeted tests
- broader unit/integration tests when the issue changes shared behavior
- lint
- typecheck
- any repo-specific validation explicitly required by the issue/spec/CI

Rules:

- run the smallest truthful validation set first, then widen as needed
- if an issue changes shared contracts, persistence, schemas, or CI-facing behavior, broaden validation accordingly
- if adversarial review finds a defect, fix it and re-run the relevant validation
- do not report `PASS` if required validation was skipped
- do not rely on stale earlier test runs after material code changes

## Before closing the issue, confirm all of the following

- branch was pushed
- merge to `main` succeeded
- `main` contains the final code
- validation passed
- acceptance criteria are tied to tests
- issue is ready to close
- branch is deleted or intentionally retained with explanation

## Never do this

- never close the issue while the work exists only on a feature branch
- never report completion based only on branch state
- never leave divergent branch/main implementations for the same issue without explicitly calling that out and resolving it
- never treat aggregate coverage as sufficient proof that an issue is done
- never defer missing acceptance tests to a later cleanup pass unless the issue explicitly says so

## Git / GitHub closeout requirements

Follow `.agents/skills/work-next-issue-in-given-epic/assets/git-and-github-closeout.md` exactly.

Minimum required closeout:

- review `git status`, `git diff`, current branch, and remotes before finalizing
- create or confirm the correct issue branch from current `main`
- commit with a clear, issue-linked message
- push the issue branch and verify the push succeeded
- merge the issue branch into `main`
- verify `main` contains the intended final content
- add a substantive completion note on the child issue
- update the EPIC checklist / progress note
- close the child issue
- if the EPIC is now done, close the EPIC
- delete the issue branch unless intentionally retained

If the environment or permissions prevent push/merge/closeout, the run is **not PASS**. In that case, output **FAIL** and state the exact external blocker.

## Git / GitHub closeout procedure summary

Treat this as mandatory, not optional.

### A. Branch creation requirements

Before implementation begins:

- sync or inspect current `main`
- create an issue branch from current `main`
- use branch naming:
  - `issue-<number>-<short-slug>`

Do not implement issue work directly on `main` unless the user explicitly instructs you to do so.

### B. Verify repo state before finalizing

Check at minimum:

- `git status --short`
- `git branch --show-current`
- `git remote -v`
- `git diff --stat`
- `git log --oneline -n 5`

If the selected issue changed code or docs, those changes must be committed before the run can pass.

### C. Commit requirements

- stage only the files required for the selected issue
- use a commit message that clearly references the issue, e.g. `P1-7: implement profile loader (#15)`
- if multiple commits are warranted, that is acceptable, but the final output must identify the commit sha that represents the completed issue on the issue branch

### D. Push requirements

- push the issue branch to the correct remote
- verify push success before posting GitHub completion notes
- record the exact remote/branch push target in the final output

### E. Merge requirements

- merge the issue branch back into `main` only after validation passes
- prefer a clean merge/rebase path that preserves an understandable history
- do not leave the completed work only on the feature branch
- after merge, verify `main` contains the final intended content
- if merge/rebase changes the final sha on `main`, report both:
  - final issue-branch commit sha
  - final main commit sha

### F. Child issue note requirements

Post a substantive completion note that includes:

- what was implemented
- key files changed
- tests/validation run
- adversarial review findings
- corrections made after review
- issue branch name
- final issue-branch commit sha
- final main commit sha if different
- explicit confirmation that `main` now contains the completed work

### G. EPIC update requirements

Update the EPIC so the completed child issue is checked off and status is clear.

Add a brief EPIC comment that includes:

- which child issue was completed
- issue branch name
- final issue-branch commit sha
- final main commit sha if different
- whether anything remains in the EPIC
- whether the EPIC is now complete

### H. Close states

- close the child issue only after implementation, validation, commit, push, merge, main verification, and notes are all done
- close the EPIC too if the completed child issue satisfied the EPIC definition of done and no required child issues remain open
- if governance/follow-up items are explicitly optional, do not keep the EPIC open just for those

### I. Branch cleanup

- delete the remote and local issue branch after successful merge and verification unless the user explicitly asked to keep it
- if the branch is intentionally retained, say so explicitly in the final output and GitHub note

### J. Failure conditions

The run must be marked `FAIL` if any of these are true:

- tests/validation required by the issue do not pass
- acceptance criteria were not actually proven by tests
- code/docs changed but were not committed
- push did not happen or failed
- merge to `main` did not happen or failed
- `main` was not verified after merge
- child issue was not updated/closed
- EPIC was not updated correctly
- EPIC should have been closed but was left open
- the work exists only on a feature branch at the end of the run

## Output contract

Use `.agents/skills/work-next-issue-in-given-epic/assets/output-format.md` exactly.

## Required output additions for acceptance-proof discipline

Within the required output format:

- in `## VALIDATION RUN`, include the exact commands used to prove the selected issue
- in `## ACCEPTANCE STATUS`, map each acceptance criterion to one or more proving tests and mark `PASS` or `FAIL`
- if a criterion is only partially proven, mark it `FAIL`
- if a criterion has no proving test, mark it `FAIL`
- do not return `PASS` in `## RESULT` unless every acceptance criterion is tied to passing proof

## Result contract

Return `PASS` only if all of the following are true:

- acceptance criteria are met
- acceptance criteria are actually proven by tests added or updated in the same issue workflow
- tests/validation pass
- issues found in adversarial review were corrected
- required code changes are committed
- required remote updates are pushed
- work was merged into `main`
- `main` was verified to contain the final implementation
- child issue notes/state are updated correctly
- EPIC notes/checklist/state are updated correctly
- branch was deleted or intentionally retained with explanation

Otherwise return `FAIL`.
