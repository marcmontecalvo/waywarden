# Damage Control for WayWarden

This is a WayWarden adaptation of the core idea from Pi's damage-control spec: intercept risky actions in real time and apply operator-defined rules before destructive work happens.

## Goal

Prevent obvious self-inflicted damage while preserving useful autonomy.

## High-value protections

### 1. Dangerous command interception
Inspect shell or task-runner execution before the command is executed.

Initial patterns to flag or block:
- `rm -rf`
- recursive deletes outside approved temp/work directories
- broad chmod/chown
- force pushes and destructive git resets
- package manager uninstall/prune commands in the wrong directory
- disk-wide moves/copies targeting sensitive locations

### 2. Path-based policy
Support path classes such as:
- **zero access**: agent must not read or touch
- **read only**: agent may inspect but not modify
- **no delete**: edits allowed, deletion forbidden
- **approved work dirs**: normal operation allowed

### 3. Tool-level interception
Apply policies not only to shell execution but also to file-oriented tools and extension-provided tools.

### 4. Audit trail
Every blocked or overridden action should produce a structured record with:
- timestamp
- actor/agent
- attempted tool/action
- matched rule
- final disposition

## Recommended rule file

A project-local policy file such as:

```yaml
guardrails:
  zero_access_paths:
    - ".git/"
    - "secrets/"
  read_only_paths:
    - "docs/archive/"
  no_delete_paths:
    - "apps/backend/src/"
  blocked_commands:
    - "rm -rf"
    - "git push --force"
```

## Important design choice

WayWarden should distinguish between:
- **hard block**
- **warn and require confirmation**
- **audit only**

Not every risky action needs the same enforcement level.

## Implementation advice

Start with:
1. shell command interception
2. path policy for built-in file tools
3. structured logging
4. minimal project-local rules file

Do not start with a giant policy language.
