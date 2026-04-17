# ADR 0005: Approval and policy model

## Status
Accepted

## Decision
Tool invocations are governed by explicit policy presets and classified as:
- auto-allow
- approval-required
- forbidden

## Policy presets
The harness should support at least:
- `yolo`
- `ask`
- `allowlist`
- `custom`

For local operator-driven development, `yolo` may be the default preset. This must still be implemented as a policy preset, not as hidden behavior.

## Examples
Auto-allow:
- retrieval
- memory reads
- task creation
- knowledge reads

Approval-required:
- send email
- edit calendar
- repo-changing coding actions in non-yolo profiles
- HA write actions in non-yolo profiles

Forbidden:
- arbitrary root shell outside declared policy
- silent policy rewrites
- autonomous HA config edits

## Rule
Even in YOLO-oriented use, policy remains explicit, inspectable, and replaceable.
