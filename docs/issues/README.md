---
type: issue
title: "Issue Tracking — Moved to GitHub Issues"
status: Active
date: 2026-04-17
issue_type: index
priority: navigation
phase: harness-core
owner: marcmontecalvo
target_milestone: null
---

# Issue tracking has moved

**GitHub Issues is the single source of truth.** As of 2026-04-17, all epic and issue tracking lives at:

- Issues: https://github.com/marcmontecalvo/waywarden/issues
- Milestones: https://github.com/marcmontecalvo/waywarden/milestones
- Labels: https://github.com/marcmontecalvo/waywarden/labels

The markdown files in this directory are retained for **historical reference only** and must not be edited to track new work.

## Why

- One backlog, one source of truth.
- Native tooling: milestones, labels, dependencies via task lists, search, API, CLI (`gh`).
- Multi-agent + human collaboration works out of the box; md-file triage does not.
- `gh issue` and the GitHub API make automation and dashboards cheap.

## Conventions

### Milestones
- `v1-harness` — harness core + first profile (EA).
- `v2-coding` — coding profile, till-done loop, teams/pipelines.
- `v3-home` — home profile, HA adapters, optional reflection work.

### Labels
- **Priority**: `now`, `next`, `soon`, `later`, `whenever`
- **State**: `ready`, `blocked`, `design`, `spike`
- **Area**: `harness-core`, `profile-ea`, `profile-coding`, `profile-home`, `policy-approvals`, `memory-knowledge`, `extensions`, `ops`, `docs`
- **Phase**: `phase-p0`, `phase-p1`, … (added as phases start)
- **Epic**: `epic` (on parent tracking issues only)

### Epics
- One issue per epic, labeled `epic` + the relevant phase label.
- Body contains a checklist linking every sub-issue by number.
- Closed when all sub-issues are closed and exit criteria met.

### Issues
- Title prefix `Pn-k:` (e.g. `P1-3: Health endpoints`) to make phase + ordering obvious.
- Body references the parent epic on the first line: `Parent epic: #N`.
- Every issue links to the ADRs/specs it implements.
- Use `Depends on: #X` lines for blocking relationships.

### Done
Unchanged — see [definition-of-done.md](definition-of-done.md).

## Retained (historical) files in this dir

These predate the move and will not be updated going forward. They remain only so prior context and phase intent is readable from the repo:

- [epics.md](epics.md) — the original E1–E10 bucketing
- [milestones.md](milestones.md) — the original M1–M6 milestones (superseded by GitHub milestones)
- [ordered-issues.md](ordered-issues.md) — the original flat ordering (superseded by GitHub issues)
- [definition-of-done.md](definition-of-done.md) — still authoritative

## Current open epics

- P0 Foundations — https://github.com/marcmontecalvo/waywarden/issues/1
- P1 Core boots — https://github.com/marcmontecalvo/waywarden/issues/2

Later phases (P2–P7) will be opened as epics when the preceding phase nears exit.
