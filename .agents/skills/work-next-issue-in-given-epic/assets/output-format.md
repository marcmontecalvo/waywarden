# Required output format

Return exactly these sections, in this order:

## EPIC
- URL
- title

## SELECTED ISSUE
- issue number
- title
- URL
- why this was chosen as the next actionable issue

## PLAN
- concise bullets describing the implementation approach

## IMPLEMENTATION
- concise bullets of what changed

## FILES CHANGED
- one bullet per file changed

## VALIDATION RUN
- exact commands run
- pass/fail for each

## ADVERSARIAL REVIEW
- bullet list of defects found
- write `none` if none

## CORRECTIONS AFTER REVIEW
- bullet list
- write `none` if none

## GIT STATUS
- active branch
- whether working tree is clean
- commit sha for the final implementation commit
- push target used

## GITHUB UPDATES
- what was posted to the child issue
- whether the child issue was closed
- how the EPIC was updated
- whether the EPIC was closed

## ACCEPTANCE STATUS
- one bullet per acceptance criterion with `PASS` or `FAIL`

## RESULT
- `PASS` only if all of the following are true:
  - acceptance criteria are met
  - tests/validation pass
  - issues found in adversarial review were corrected
  - required code changes are committed
  - required remote updates are pushed
  - child issue notes/state are updated correctly
  - EPIC notes/checklist/state are updated correctly
- otherwise `FAIL`
