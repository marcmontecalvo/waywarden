---
name: work-next-issue-in-given-epic
description: Resolve the next actionable child issue from a GitHub EPIC, implement it fully, adversarially review/fix it, then commit, push, update GitHub, and close the issue and epic when appropriate.
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
4. Implement the selected issue with tight scope.
5. Run validation.
6. Perform adversarial review.
7. Correct defects and re-run validation until the work genuinely passes.
8. **Commit and push the code changes.**
9. **Post completion notes to the child issue and the EPIC.**
10. **Close the child issue.**
11. **If that child issue completed the EPIC, update and close the EPIC too.**
12. Return the required output format.

## Non-negotiable rules

- Do not stop until tests pass.
- Do not claim success while the working tree is dirty unless the remaining dirt is deliberate, explained, and outside the selected issue.
- Do not claim success unless required repo changes are committed.
- Do not claim success unless required remote updates are pushed.
- Do not claim success unless GitHub issue notes/checklists/state reflect the finished work.
- Do not leave the child issue open if the work is complete.
- Do not leave the EPIC open if this was the last required item and the EPIC's definition of done is satisfied.
- Do not use fake-success placeholders, TODO-only implementations, or hand-wavy closeout comments.
- Keep scope tight to the selected issue unless a directly related defect blocks truthful completion.
- Be aggressive about token discipline during repo inspection and validation. Prefer `rtk`-wrapped shell commands for noisy output (git diffs/status, ripgrep/find scans, test runs, coverage, build logs) unless raw output is required to resolve the issue truthfully.

## Git / GitHub closeout requirements

Follow `.agents/skills/work-next-issue-in-given-epic/assets/git-and-github-closeout.md` exactly.

Minimum required closeout:

- review `git status`, `git diff`, current branch, and remotes before finalizing
- commit with a clear, issue-linked message
- push to the correct remote/branch or create the required branch and push it
- verify the push succeeded
- add a substantive completion note on the child issue
- update the EPIC checklist / progress note
- close the child issue
- if the EPIC is now done, close the EPIC

If the environment or permissions prevent push/closeout, the run is **not PASS**. In that case, output **FAIL** and state the exact external blocker.

## Output contract

Use `.agents/skills/work-next-issue-in-given-epic/assets/output-format.md` exactly.
