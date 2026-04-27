## Whole EPIC execution

When the user says `work epic X`, `we X`, or provides a GitHub EPIC issue URL and asks to complete the EPIC, open and follow:

`.agents/skills/work-entire-epic/SKILL.md`

Do not invent a separate workflow.

The whole-EPIC skill loops over the existing next-issue skill:

`.agents/skills/work-next-issue-in-given-epic/SKILL.md`

Critical input rule:

- `we 4` means EPIC `P4`, not GitHub issue `#4`.
- `work epic 4` means EPIC `P4`, not GitHub issue `#4`.
- `we P4` means EPIC `P4`.
- `we #4`, `we issue 4`, or a URL ending in `/issues/4` means exact GitHub issue `#4`.

Rules:

- Resolve the EPIC first.
- Review all currently open child issues.
- Select the first open actionable child issue.
- Complete exactly one child issue at a time.
- Use TDD or test-as-early-as-practical discipline.
- Run adversarial review after implementation.
- Fix defects found in review.
- Re-run validation.
- Merge to `main`.
- Verify `main`.
- Update and close the child issue.
- Update the EPIC.
- Then move to the next child issue.
- Stop only when the EPIC is complete or truly blocked.

Do not work directly on `main`.

Do not move to the next child issue while the current child issue is incomplete.

Do not close the EPIC while required child issues remain open.
