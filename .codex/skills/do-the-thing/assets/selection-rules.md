# Issue Selection Rules

When given an EPIC URL:

1. Read the full EPIC issue body.
2. Look for an ordered checklist or ordered child issue list.
3. Determine the next open actionable child issue using this priority:
   1. first unchecked child issue in the intended execution order
   2. if ordering is unclear, first open child issue explicitly tied to the current phase
   3. if multiple candidates remain, choose the one whose blocking dependencies are already satisfied
4. If the first open issue is blocked by an incomplete prerequisite, skip to the next actionable one and state why.
5. Read the selected child issue fully before coding.
6. Capture acceptance criteria and non-goals before implementation starts.

## If the EPIC format is weak
Infer carefully from:
- checklist order
- issue numbering scheme
- explicit dependency notes
- phase headers
- issue titles and descriptions

## If there is no clean child issue list
Prefer the clearest open linked issue that:
- belongs to the active phase
- has explicit acceptance criteria
- has satisfied prerequisites

Explain the choice in the final output.
