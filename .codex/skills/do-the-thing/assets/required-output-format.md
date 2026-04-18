# Required Output Format

Return exactly these sections, in this order.

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

## TESTS RUN
- exact commands run
- pass/fail for each

## ADVERSARIAL REVIEW
- bullet list of defects found
- write `none` if none

## CORRECTIONS AFTER REVIEW
- bullet list
- write `none` if none

## GITHUB UPDATES
- what was posted to the child issue
- whether the child issue was closed
- how the EPIC was updated

## ACCEPTANCE STATUS
- one bullet per acceptance criterion with `PASS` or `FAIL`

## RESULT
- `PASS` if the issue is fully complete, validated, reviewed, corrected, and closed out
- `FAIL` otherwise

If the result would be FAIL, continue working instead of stopping unless blocked by a true external constraint.
