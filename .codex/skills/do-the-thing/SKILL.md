---
name: do-the-thing
description: Execute the next open actionable child issue from a GitHub EPIC, implement it fully, adversarially review the result, fix defects, update GitHub, and stop only when tests pass and the issue is truthfully complete.
---

# Do The Thing

Use this skill when the user gives you a GitHub EPIC issue URL and wants you to carry the next issue all the way through implementation, validation, adversarial review, correction, and GitHub closeout.

## Inputs
- One GitHub EPIC issue URL.
- The repo associated with that EPIC.
- Any planning or acceptance context linked from the EPIC or child issue.

## Output contract
Use the final output format in `assets/required-output-format.md`.

## Workflow

1. Read the EPIC fully.
2. Resolve the next open actionable child issue using the rules in `assets/selection-rules.md`.
3. Run repo-intelligence preflight using `assets/codegraph-preflight.md` and `assets/repo-intelligence-checklist.md`.
4. Read the selected child issue fully.
5. Extract:
   - goal
   - scope
   - non-goals
   - acceptance criteria
   - required tests
   - dependencies
6. Implement the issue exactly as specified.
7. Run validation.
8. Perform a strict adversarial review of the work you just implemented.
9. Fix any defect found.
10. Re-run validation.
11. Repeat review-and-fix until the issue genuinely passes.
12. Post GitHub notes using `assets/github-closeout-checklist.md`.
13. Close the child issue.
14. Check it off in the EPIC.
15. Return the required final output.

## Non-negotiable rules
- Do not stop until tests pass.
- Do not leave partial work.
- Do not mark an issue complete unless all acceptance criteria are satisfied in reality.
- Do not use fake-success responses, TODO-only implementations, or placeholder behavior that pretends to be complete.
- Keep scope tight to the selected issue unless a directly related defect must be fixed for truthful completion.
- Preserve non-goals and boundary constraints.
- If the EPIC is slightly messy, infer the intended order conservatively and continue.

## Issue selection behavior
Follow `assets/selection-rules.md`.

In short:
- prefer the first unchecked child issue in the intended execution order
- if the ordering is unclear, prefer the first open child issue in the current phase whose prerequisites are satisfied
- if dependencies block the first open issue, choose the next truly actionable one and explain why


## Repo-intelligence preflight
Follow `assets/codegraph-preflight.md` and `assets/repo-intelligence-checklist.md`.

In short:
- prefer CodeGraph when the repo/task complexity makes indexing worthwhile
- use it for architecture tracing and cross-file impact analysis
- do not require it for normal operation
- fall back cleanly to normal exploration if unavailable, stale, or not worth the setup cost
- validate touched files directly before making changes

## Implementation behavior
- Satisfy each acceptance criterion explicitly.
- Keep naming, structure, and patterns consistent with the repo.
- Update tests and docs when required by the issue.
- Avoid broad architectural churn unless required for correctness.
- Preserve already-good scaffolding if removing it would be churn without value.

## Validation behavior
Run the repo’s relevant validation for the touched area, including:
- targeted tests
- broader tests if repo conventions require them
- lint/format/type checks when relevant to touched files

Do not stop at one passing targeted test if broader validation is expected.

## Adversarial review behavior
Review your own implementation as if trying to fail it.

Check for:
- incomplete acceptance coverage
- hidden scope creep
- brittle tests
- weak error handling
- bad assumptions
- missing edge cases
- docs drift
- misleading placeholder behavior
- incorrect issue interpretation
- typing, lint, import, or boundary problems

Be strict.

## GitHub closeout behavior
Follow `assets/github-closeout-checklist.md`.

The child issue closeout note must include:
- what was implemented
- tests added or updated
- validation run
- adversarial review findings
- corrections made after review

The EPIC update must:
- check off the completed child issue
- add a brief status note if useful

## If blocked
Only stop short of PASS for a true external blocker that you cannot overcome from the available repo/tools.
If blocked, explain the blocker precisely in the required output format.

## Examples
- `/DoTheThing https://github.com/marcmontecalvo/waywarden/issues/2`
- `Work the next open issue in this EPIC and do full implementation + adversarial review + closeout: <epic-url>`
