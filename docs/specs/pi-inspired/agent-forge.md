# Agent Forge for WayWarden

This is a cautious WayWarden adaptation of Pi's Agent Forge concept: the system can expand its own capabilities by creating new tools or capabilities.

## Why this is interesting

It can turn repeated manual workflows into durable reusable capabilities.

## Why this is dangerous

It can also create unreviewed power, hidden complexity, and unsafe execution paths.

## Recommendation

Treat this as a later-stage feature, behind review gates.

## Safe model

### Allowed outputs
Initially, WayWarden should only be allowed to generate:
- new prompt templates
- new agent definitions
- new capability packages
- draft extension/plugin files

### Disallowed in early versions
- hot-loading arbitrary executable code without review
- automatically enabling newly generated tools
- modifying core runtime behavior without approval

## Suggested lifecycle

1. Propose new capability
2. Generate files in a sandboxed/draft location
3. Run validation/lint/tests if applicable
4. Require human review or explicit promotion
5. Only then enable/discover the new capability

## Required safeguards

- registry of generated artifacts
- origin metadata
- diff visibility
- promotion workflow
- rollback/removal path
- policy integration with damage-control

## Recommendation

Do not let WayWarden self-install executable power in v1.
Let it draft reusable artifacts first.
