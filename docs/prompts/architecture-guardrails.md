Before writing implementation code, create and respect these ADRs:
- 0001-context-and-goals
- 0002-ea-only-substrate
- 0003-memory-vs-knowledge
- 0004-skill-contract
- 0005-approval-model
- 0006-v1-v2-v3-roadmap
- 0007-good-and-bad-patterns

Each ADR must be concise, opinionated, and enforceable.
Then scaffold only the code required by those ADRs.

Important:
- treat the harness as one core plus profile packs
- do not hardwire the codebase to one UI
- do not assume Honcho or LLM-Wiki are permanent
- keep shared assets at the root and filter them into profiles
