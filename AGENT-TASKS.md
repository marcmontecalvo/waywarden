# Waywarden task entrypoints

## ww-next <epic>
Run the repo-local workflow for the next actionable child issue in the given EPIC.

Procedure:
1. Open `.agents/skills/work-next-issue-in-given-epic/SKILL.md`
2. Treat that file as authoritative
3. Do not use any global skill resolver
4. Do not search for alternate skills if the file exists
5. Use canonical `gh` CLI issue-read commands defined by that skill
6. Accept either:
   - a bare issue number for the EPIC
   - a full GitHub issue URL

Examples:
- `ww-next 35`
- `ww-next https://github.com/marcmontecalvo/waywarden/issues/35`