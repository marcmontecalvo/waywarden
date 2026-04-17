# ADR 0008: Coding-agent prompts

See `docs/prompts/` for the actual prompts.

## Rule
Prompts do not define architecture by themselves.
They enforce and accelerate implementation of the ADRs.

## Additional rule
Reusable behavior such as:
- adversarial review
- advisor passes
- till-done loops
- workflow repetition

should prefer routines, teams, pipelines, and policy-backed execution over prompt-only tricks.
