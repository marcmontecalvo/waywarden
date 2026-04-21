---
name: work-next-issue-in-given-epic
description: Resolve the next actionable child issue from a GitHub EPIC, implement it fully, adversarially review/fix it, then commit, push, merge to main, verify main, update GitHub, close the issue, and close the epic when appropriate.
---

# work-next-issue-in-given-epic

Use this skill when the user gives you a GitHub EPIC issue URL and wants fully autonomous execution of the **next open actionable child issue**.

## Inputs

- GitHub EPIC issue URL
- Current repo working tree
- Repo issue bodies/comments

## Mandatory workflow

1. Resolve the active EPIC and identify the next actionable child issue.
2. Read the child issue body, comments, linked specs, and any related acceptance criteria.
3. Run repo-intelligence preflight (`.agents/skills/work-next-issue-in-given-epic/assets/repo-intelligence-checklist.md`). Use CodeGraph if available and worthwhile; otherwise fall back cleanly.
4. Create a fresh issue branch from current `main`.
5. Implement the selected issue with tight scope on that branch.
6. Run validation on that branch.
7. Perform adversarial review.
8. Correct defects and re-run validation until the work genuinely passes.
9. **Commit the code changes on the issue branch.**
10. **Push the issue branch.**
11. **Merge the issue branch into `main`.**
12. **Verify `main` contains the final intended result.**
13. **Post completion notes to the child issue and the EPIC.**
14. **Close the child issue.**
15. **If that child issue completed the EPIC, update and close the EPIC too.**
16. **Delete the issue branch unless the user explicitly asked to keep it.**
17. Return the required output format.

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
- Be aggressive about token discipline during repo inspection and validation. Prefer `rtk`-wrapped shell commands for noisy output (git diffs/status, ripgrep/find scans, test runs, coverage, build logs) unless raw output is required to resolve the issue truthfully.

## Mandatory GitHub issue workflow

For every issue worked with this skill, follow this exact sequence unless the user explicitly overrides it:

1. Create a fresh issue branch from current `main`
2. Implement the issue on that branch
3. Run required validation on that branch
4. Push the branch
5. Merge branch into `main`
6. Verify `main` contains the final intended result
7. Close the issue
8. Delete the branch

## Canonical GitHub CLI reads
Use `gh` CLI only for GitHub operations.

### Issue read commands
Start with the minimum stable issue read:

```bash
gh issue view <issue-number> --json number,title,body,state,url,labels
```
*If the issue has comments that may contain relevant information, add `comments` to the JSON fields*

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

1) stop retrying variants blindly
2) fall back immediately to:
``` bash
gh issue view <issue-number> --json number,title,body,state,url,labels
```
3) continue from there



### Branch naming
Use:
- `issue-<issue-number>-<short-slug>`

### Before closing the issue, confirm all of the following
- branch was pushed
- merge to `main` succeeded
- `main` contains the final code
- validation passed
- issue is ready to close
- branch is deleted or intentionally retained with explanation

### Never do this
- never close the issue while the work exists only on a feature branch
- never report completion based only on branch state
- never leave divergent branch/main implementations for the same issue without explicitly calling that out and resolving it

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

## Output contract

Use `.agents/skills/work-next-issue-in-given-epic/assets/output-format.md` exactly.
