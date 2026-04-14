# ADR 0005: Approval model

## Status
Accepted

## Decision
Tool invocations are classified as:
- auto-allow
- approval-required
- forbidden

## Default posture
Conservative.

## Examples
Auto-allow:
- retrieval
- memory reads
- task creation

Approval-required:
- send email
- edit calendar
- repo-changing coding handoff
- HA write actions

Forbidden:
- arbitrary root shell
- policy rewrites
- autonomous HA config edits
