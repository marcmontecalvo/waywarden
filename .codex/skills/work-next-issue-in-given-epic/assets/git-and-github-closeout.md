# Git and GitHub closeout procedure

Treat this as mandatory, not optional.

## A. Verify repo state before finalizing

Check at minimum:

- `git status --short`
- `git branch --show-current`
- `git remote -v`
- `git diff --stat`
- `git log --oneline -n 5`

If the selected issue changed code or docs, those changes must be committed before the run can pass.

## B. Commit requirements

- Stage only the files required for the selected issue.
- Use a commit message that clearly references the issue, e.g. `P1-7: implement profile loader (#15)`.
- If multiple commits are warranted, that is acceptable, but the final output must identify the commit sha that represents the completed issue.

## C. Push requirements

- Push the implementation commit(s) to the correct remote/branch for the repo workflow.
- If the repo expects feature branches, create/use an issue-specific branch and push it.
- If the repo expects direct pushes to the active branch, push there.
- Verify push success before posting GitHub completion notes.

## D. Child issue note requirements

Post a substantive completion note that includes:

- what was implemented
- key files changed
- tests/validation run
- adversarial review findings
- corrections made after review
- final commit sha
- branch name

## E. EPIC update requirements

Update the EPIC so the completed child issue is checked off and status is clear.

Add a brief EPIC comment that includes:

- which child issue was completed
- commit sha / branch
- whether anything remains in the EPIC
- whether the EPIC is now complete

## F. Close states

- Close the child issue once implementation, validation, commit, push, and notes are all done.
- Close the EPIC too if the completed child issue satisfied the EPIC definition of done and no required child issues remain open.
- If governance/follow-up items are explicitly optional, do not keep the EPIC open just for those.

## G. Failure conditions

The run must be marked `FAIL` if any of these are true:

- tests/validation required by the issue do not pass
- code/docs changed but were not committed
- push did not happen or failed
- child issue was not updated/closed
- EPIC was not updated correctly
- EPIC should have been closed but was left open
