# Git and GitHub closeout procedure

Treat this as mandatory, not optional.

## A. Branch creation requirements

Before implementation begins:

- sync or inspect current `main`
- create an issue branch from current `main`
- use branch naming:
  - `issue-<number>-<short-slug>`

Do not implement issue work directly on `main` unless the user explicitly instructs you to do so.

## B. Verify repo state before finalizing

Check at minimum:

- `git status --short`
- `git branch --show-current`
- `git remote -v`
- `git diff --stat`
- `git log --oneline -n 5`

If the selected issue changed code or docs, those changes must be committed before the run can pass.

## C. Commit requirements

- Stage only the files required for the selected issue.
- Use a commit message that clearly references the issue, e.g. `P1-7: implement profile loader (#15)`.
- If multiple commits are warranted, that is acceptable, but the final output must identify the commit sha that represents the completed issue on the issue branch.

## D. Push requirements

- Push the issue branch to the correct remote.
- Verify push success before posting GitHub completion notes.
- Record the exact remote/branch push target in the final output.

## E. Merge requirements

- Merge the issue branch back into `main` only after validation passes.
- Prefer a clean merge/rebase path that preserves an understandable history.
- Do not leave the completed work only on the feature branch.
- After merge, verify `main` contains the final intended content.
- If merge/rebase changes the final sha on `main`, report both:
  - final issue-branch commit sha
  - final main commit sha

## F. Child issue note requirements

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

## G. EPIC update requirements

Update the EPIC so the completed child issue is checked off and status is clear.

Add a brief EPIC comment that includes:

- which child issue was completed
- issue branch name
- final issue-branch commit sha
- final main commit sha if different
- whether anything remains in the EPIC
- whether the EPIC is now complete

## H. Close states

- Close the child issue only after implementation, validation, commit, push, merge, main verification, and notes are all done.
- Close the EPIC too if the completed child issue satisfied the EPIC definition of done and no required child issues remain open.
- If governance/follow-up items are explicitly optional, do not keep the EPIC open just for those.

## I. Branch cleanup

- Delete the remote and local issue branch after successful merge and verification unless the user explicitly asked to keep it.
- If the branch is intentionally retained, say so explicitly in the final output and GitHub note.

## J. Failure conditions

The run must be marked `FAIL` if any of these are true:

- tests/validation required by the issue do not pass
- code/docs changed but were not committed
- push did not happen or failed
- merge to `main` did not happen or failed
- `main` was not verified after merge
- child issue was not updated/closed
- EPIC was not updated correctly
- EPIC should have been closed but was left open
- the work exists only on a feature branch at the end of the run
