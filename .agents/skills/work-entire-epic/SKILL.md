---
name: work-entire-epic
description: Work every open actionable child issue in a GitHub EPIC by repeatedly invoking the repo-local work-next-issue-in-given-epic workflow until the EPIC is complete or blocked.
---

# work-entire-epic

Use this skill when the user gives an EPIC number, phase number, EPIC name, or GitHub EPIC issue URL and wants the whole EPIC completed.

This skill is intentionally a thin loop around the repo-local next-issue skill:

`.agents/skills/work-next-issue-in-given-epic/SKILL.md`

Do not invent a new implementation workflow.

Do not use a global skill registry.

Open repo-local SKILL.md files directly.

## Critical input-resolution rule

A bare number is **not automatically a GitHub issue number**.

Interpret inputs as follows:

- `we 4` means **work EPIC P4**, not GitHub issue `#4`.
- `work epic 4` means **work EPIC P4**, not GitHub issue `#4`.
- `work P4` means **work EPIC P4**.
- `we P4` means **work EPIC P4**.
- `we issue 4` means GitHub issue `#4`.
- `we #4` means GitHub issue `#4`.
- `we https://github.com/<owner>/<repo>/issues/<number>` means use that exact GitHub issue as the EPIC candidate.

For the common shorthand `we 4`, first resolve the EPIC by searching open issues for an issue whose title/labels/body indicate `[EPIC] P4` / `phase-p4` / `P4:`.

Only call `gh issue view 4` when the user explicitly says `issue 4`, `#4`, or provides `/issues/4`.

## Accepted input forms

- `work epic 4`
- `work epic P4`
- `work P4`
- `we 4`
- `we P4`
- `we issue 63`
- `we #63`
- `we https://github.com/marcmontecalvo/waywarden/issues/63`
- direct GitHub EPIC issue URL

## Goal

Complete every open actionable child issue in the EPIC.

For each child issue:

1. select the first open actionable child issue
2. follow `.agents/skills/work-next-issue-in-given-epic/SKILL.md` exactly
3. run baseline validation before edits
4. implement issue-scoped tests and code
5. run `make format`, `make lint`, `make test`, and typecheck when available before every commit
6. review the implementation adversarially
7. fix any defects found and rerun validation
8. commit, push, merge, verify `main`, and run post-merge validation
9. update and close the child issue
10. update the EPIC
11. delete the issue branch unless intentionally retained
12. move to the next open actionable child issue

Continue until:

- the EPIC has no remaining open actionable child issues, or
- the EPIC is blocked by a real dependency requiring human input.

## Phase 1: Resolve the EPIC

### A. If input is a GitHub issue URL

Extract the issue number from the URL and read it directly:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels,comments
```

The issue must be treated as the EPIC candidate. If it is not labeled/title-shaped like an EPIC, stop and report `FAIL` unless the user explicitly said to treat it as the EPIC.

### B. If input is `#N` or `issue N`

Read that issue number directly:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels,comments
```

The issue must be treated as the EPIC candidate.

### C. If input is a bare number, such as `4`

Normalize it to phase key `P4`.

Do **not** read issue `#4`.

Search for the EPIC issue using `gh issue list`:

```bash
gh issue list \
  --state all \
  --search "repo:$(gh repo view --json nameWithOwner --jq .nameWithOwner) P4 in:title" \
  --json number,title,state,url,labels \
  --limit 50
```

Prefer the result that matches all or most of:

- title starts with `[EPIC] P4`
- title contains `P4:`
- has label `epic`
- has label `phase-p4`

Then read that issue as the EPIC:

```bash
gh issue view <resolved-epic-number> --json number,title,body,state,url,labels,comments
```

### D. If input is `P4`

Use the same EPIC search flow as a bare number normalized to `P4`.

### E. If multiple EPIC candidates match

Choose the issue with:

1. `epic` label
2. matching `phase-pN` label
3. title prefix `[EPIC] PN`
4. open state over closed state

If still ambiguous, stop with `FAIL` and list candidates.

## Phase 2: Read child issues

Determine child issues from the EPIC body/checklist/comments.

Prefer explicit GitHub issue links and checklist/order-of-execution items in the EPIC body.

Read each child issue that appears in the EPIC body:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels,comments
```

Review all child issues that are still open.

Identify the first open actionable child issue according to the EPIC order of execution.

Respect:

- explicit dependencies
- `blocked` labels
- design/spike labels if they indicate not executable
- sequencing notes in the EPIC body

Do not silently skip open child issues.

## Phase 3: Child issue loop

For each selected child issue, run the existing next-issue workflow exactly:

```md
Open and follow:

.agents/skills/work-next-issue-in-given-epic/SKILL.md
```

The selected child issue must go through:

1. repo intelligence preflight
2. branch from current `main`
3. mandatory baseline gate before edits:
   - `git status --short`
   - `make lint`
   - `make test`
   - typecheck when the repo exposes it
4. acceptance criteria identification
5. tests first or tests as early as practical
6. implementation
7. targeted and broadened validation as needed
8. adversarial review
9. corrections after review
10. full pre-commit gate:
    - `git status --short`
    - `make format`
    - `make lint`
    - `make test`
    - typecheck when the repo exposes it
11. commit
12. push and verify push success
13. merge to `main`
14. verify `main`
15. post-merge gate on `main`:
    - `make lint`
    - `make test`
    - typecheck when the repo exposes it
16. child issue completion note
17. EPIC update
18. child issue close
19. branch cleanup

Do not proceed to the next child issue unless the current child issue reaches `PASS` under the next-issue skill’s result contract.

If the current child issue returns `FAIL`, stop the EPIC loop and report the blocker.

## Baseline and failure attribution rule

A child issue may claim a validation failure is preexisting only if the exact failure was captured in the baseline gate before edits began.

Rules:

- If baseline checks pass, later lint/test/typecheck failures belong to the current issue until fixed or rigorously proven otherwise.
- If baseline checks fail, stop the EPIC loop and report `FAIL` unless the current child issue explicitly exists to repair that baseline failure or the user explicitly told you to continue.
- If the agent skipped the baseline gate, it may not call later failures preexisting. It must fix them or revert the relevant changes.
- Do not continue to the next child issue with red validation from the previous issue.
- Do not batch multiple child issues into one commit just to avoid a failing intermediate state.

## Phase 3: Adversarial review loop

For every child issue, explicitly run this loop:

1. Review the final diff against the issue acceptance criteria.
2. Review tests and confirm they prove the acceptance criteria.
3. Look for:
   - missing tests
   - shallow tests
   - acceptance criteria not proven
   - overbroad scope
   - broken public contracts
   - schema/migration issues
   - bad error handling
   - inconsistent docs
   - uncommitted files
   - branch/main divergence
   - issue not actually updated
   - skipped format/lint/test/typecheck gates
   - failures incorrectly described as preexisting
4. If defects are found:
   - fix them
   - rerun `make format`, `make lint`, `make test`, targeted tests, and typecheck when available as appropriate
   - repeat adversarial review
5. Continue until no blocking defects remain.

Do not accept “review found issues but they can be fixed later.”

## Phase 4: EPIC completion

After each completed child issue:

1. Re-read the EPIC.
2. Re-read remaining child issues.
3. Determine whether any required child issues remain open.
4. If more remain, continue.
5. If none remain:
   - update the EPIC checklist/status
   - add a final EPIC completion comment
   - run final validation from `main`:
     - `make lint`
     - `make test`
     - typecheck when available
   - close the EPIC if its definition of done is satisfied

Optional/future/governance items do not keep the EPIC open unless the EPIC explicitly says they are required.

## Non-negotiable rules

- Do not treat `we 4` as GitHub issue `#4`.
- Do not work directly on `main`.
- Do not skip tests.
- Do not skip `make format`, `make lint`, or `make test` before a commit.
- Do not commit after red lint/tests/typecheck.
- Do not claim a failure is preexisting unless the baseline gate captured it before edits.
- Do not close a child issue unless it was merged to `main`.
- Do not move to the next child issue while the current child issue is incomplete.
- Do not keep looping after a real blocker.
- Do not silently skip open child issues.
- Do not treat aggregate coverage as acceptance proof.
- Do not close the EPIC if required child issues remain open.
- Do not leave branches behind unless explicitly justified.
- Do not claim success unless GitHub issue state, branch state, validation state, and `main` state all agree.

## Required per-child issue output

For each completed child issue, include the required output from:

`.agents/skills/work-next-issue-in-given-epic/assets/output-format.md`

The per-child output must include baseline, targeted validation, pre-commit gate, post-merge gate, commit sha, push target, merge result, and issue/EPIC update status.

## Required final EPIC output

After the EPIC loop ends, return:

```md
## EPIC
- URL:
- title:
- final state: open|closed

## CHILD ISSUES COMPLETED
- #<number> <title> — PASS

## CHILD ISSUES SKIPPED OR BLOCKED
- none
```

If any were skipped or blocked:

```md
- #<number> <title> — reason:
```

Then:

```md
## VALIDATION SUMMARY
- baseline commands run before each issue: yes|no
- pre-commit gates run before each commit: yes|no
- post-merge gates run after each merge: yes|no
- commands run across issues:
- all required validation passed: yes|no
- any failures claimed preexisting: yes|no; include baseline evidence if yes

## ADVERSARIAL REVIEW SUMMARY
- issues found:
- corrections made:
- unresolved blockers:

## GIT/GITHUB SUMMARY
- all completed work merged to main: yes|no
- main verified after each issue: yes|no
- all completed child issues closed: yes|no
- EPIC updated: yes|no
- EPIC closed: yes|no
- branches deleted: yes|no

## RESULT
- PASS|FAIL
```

Return `PASS` only if the EPIC is fully complete and all required child issues reached `PASS`.

Otherwise return `FAIL`.
