# Rewind Hook Spec (WayWarden adaptation)

## Inspired by

- `nicobailon/pi-rewind-hook`

## Target behavior

- Track coding-session checkpoints
- Permit safe restore of tracked file states
- Keep retention bounded
- Surface restore options clearly to the user and/or orchestrator

## Design principles

- Restore must be explicit, not silent
- Checkpoints should be cheap to create
- State should be inspectable
- Normal git history should remain understandable

## Open decisions

- Use plain git commits, stash-like refs, patch snapshots, or hybrid storage
- Trigger points: every file write, every task boundary, or only before risky operations
- Retention policy and storage format
