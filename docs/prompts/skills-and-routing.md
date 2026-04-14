Implement:
- Skill contract
- SkillRegistry
- builtin skills:
  - project_manager
  - inbox_triage
  - scheduler
  - briefing
  - coding_handoff
  - ha_gateway

Rules:
- each skill declares name, description, model profile, required tools, required memory scopes, required knowledge scopes
- no skill bypasses approval or tool policy
