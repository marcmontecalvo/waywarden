---
name: work-entire-epic
description: Work every open actionable child issue in a GitHub EPIC by repeatedly invoking the repo-local work-next-issue-in-given-epic workflow until the EPIC is complete or blocked.
---

# work-entire-epic

Use this skill when the user gives an EPIC number, EPIC name, or GitHub EPIC issue URL and wants the whole EPIC completed.

This skill is intentionally a thin loop around the repo-local next-issue skill:

`.agents/skills/work-next-issue-in-given-epic/SKILL.md`

Do not invent a new implementation workflow.

Do not use a global skill registry.

Open the repo-local SKILL.md files directly.

## Inputs

Accepted input forms:

- `work epic 4`
- `work P4`
- `we 4`
- `we P4`
- `we https://github.com/marcmontecalvo/waywarden/issues/<number>`
- direct GitHub EPIC issue URL

If the user provides only a number like `4`, resolve it as EPIC/P4 according to the repo's existing GitHub issue conventions.

If the user provides a GitHub issue URL, treat that issue as the EPIC.

## Goal

Complete every open actionable child issue in the EPIC.

For each child issue:

1. select the first open actionable child issue
2. follow `.agents/skills/work-next-issue-in-given-epic/SKILL.md`
3. review the implementation adversarially
4. fix any defects found
5. repeat review/fix until the issue is truly complete
6. commit, push, merge, verify `main`
7. update and close the child issue
8. update the EPIC
9. delete the issue branch unless intentionally retained
10. move to the next open actionable child issue

Continue until:

- the EPIC has no remaining open actionable child issues, or
- the EPIC is blocked by a real dependency requiring human input.

## Mandatory workflow

### Phase 1: Resolve the EPIC

1. Identify the EPIC issue from the user input.
2. Read the EPIC with GitHub CLI.
3. Determine the child issues from the EPIC body/checklist/comments.
4. Review all child issues that are still open.
5. Identify the first open actionable child issue.

Use `gh` only for GitHub operations.

Start with stable reads:

```bash
gh issue view <epic-number> --json number,title,body,state,url,labels,comments
```

For child issues:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels,comments
```

Do not request unsupported GitHub JSON fields.

If a `gh --json` field fails, immediately fall back to:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels
```

### Phase 2: Child issue loop

For each selected child issue, run the existing next-issue workflow exactly:

```md
Open and follow:

.agents/skills/work-next-issue-in-given-epic/SKILL.md
```

The selected child issue must go through:

1. repo intelligence preflight
2. branch from current `main`
3. acceptance criteria identification
4. tests first or tests as early as practical
5. implementation
6. validation
7. adversarial review
8. corrections after review
9. re-validation
10. commit
11. push
12. merge to `main`
13. verify `main`
14. child issue completion note
15. EPIC update
16. child issue close
17. branch cleanup

Do not proceed to the next child issue unless the current child issue reaches `PASS`.

If the current child issue returns `FAIL`, stop the EPIC loop and report the blocker.

### Phase 3: Adversarial review loop

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
4. If defects are found:
   - fix them
   - re-run relevant validation
   - repeat adversarial review
5. Continue until no blocking defects remain.

Do not accept "review found issues but they can be fixed later."

### Phase 4: EPIC completion

After each completed child issue:

1. Re-read the EPIC.
2. Re-read remaining child issues.
3. Determine whether any required child issues remain open.
4. If more remain, continue.
5. If none remain:
   - update the EPIC checklist/status
   - add a final EPIC completion comment
   - close the EPIC if its definition of done is satisfied

Optional/future/governance items do not keep the EPIC open unless the EPIC explicitly says they are required.

## Non-negotiable rules

- Do not work directly on `main`.
- Do not skip tests.
- Do not close a child issue unless it was merged to `main`.
- Do not move to the next child issue unless the current issue reached `PASS`.
- Do not keep looping after a real blocker.
- Do not silently skip open child issues.
- Do not treat aggregate coverage as acceptance proof.
- Do not close the EPIC if required child issues remain open.
- Do not leave branches behind unless explicitly justified.
- Do not claim success unless GitHub issue state, branch state, and `main` state all agree.

## Required per-child issue output

For each completed child issue, include the required output from:

`.agents/skills/work-next-issue-in-given-epic/assets/output-format.md`

## Required final EPIC output

After the EPIC loop ends, return:

```md
## EPIC
- URL:
- title:
- final state: open|closed

## CHILD ISSUES COMPLETED
- #<number> <title> — PASS
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
- commands run across issues:
- all required validation passed: yes|no

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
