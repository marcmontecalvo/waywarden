---
type: contributing
title: "Contributing — Planning, Labels, and Done"
status: Active
date: 2026-04-27
owner: marcmontecalvo
---

# Contributing

GitHub Issues is the single source of truth for active work. This document defines the conventions that turn raw issues into a legible backlog: milestones, labels, title and body conventions, the phase map, and the Definition of Done.

- Issues: https://github.com/marcmontecalvo/waywarden/issues
- Milestones: https://github.com/marcmontecalvo/waywarden/milestones
- Labels: https://github.com/marcmontecalvo/waywarden/labels

## Definition of Done

An issue is not done unless:

- code compiles
- lint passes
- tests pass
- docs are updated if behavior changed
- config examples are updated if needed
- no TODO is hiding missing architecture work
- profile implications are considered
- token accounting or tracing implications are considered where relevant
- the change does not hardwire the harness to one UI or one provider

Completion is defined as: merged into `main`, verified on `main`, issue closed, branch deleted. Branch-only completion does not count as complete. See `AGENTS.md` — Git / issue execution policy for the full branch-to-close workflow.

## Milestones

- `v1-harness` — harness core + first profile (EA). Phases P0–P5.
- `v2-coding` — coding profile, till-done loop, teams/pipelines, scheduler, backup/restore, and workspace safety. Phases P6–P8.
- `v3-home` — home profile, HA adapters, optional reflection surfaces. Phases P9–P10.

## Labels

**Priority** (when to work on it):
- `now` — blocks current milestone; pick up next
- `next` — should land this milestone but not blocking
- `soon` — next milestone
- `later` — future milestone, keep in backlog
- `whenever` — nice-to-have, no milestone commitment

**State** (can it be worked on now):
- `ready` — all dependencies met, executable today
- `blocked` — waiting on another issue; use `Depends on: #N` in body
- `design` — needs spec or ADR before implementation
- `spike` — needs investigation before estimate is possible

**Area** (what subsystem):
- `harness-core`
- `profile-ea`
- `profile-coding`
- `profile-home`
- `policy-approvals`
- `memory-knowledge`
- `extensions`
- `ops`
- `docs`

**Phase**: `phase-p0`, `phase-p1`, … `phase-p10` (added as phases start).

**Epic**: `epic` on parent tracking issues only.

Every non-epic issue should carry one label from each of Priority, State, and Area, plus its Phase label.

## Phase map

| Phase | Epic focus                                                 | Milestone   |
|-------|------------------------------------------------------------|-------------|
| P0    | Repo foundations (tooling, CI, baseline layout)            | v1-harness  |
| P1    | Core boots (FastAPI, config, profile loader, CLI)          | v1-harness  |
| P2    | Persistence, ORM, migrations, extension base contract      | v1-harness  |
| P3    | Memory + knowledge adapters (Honcho, LLM-Wiki)             | v1-harness  |
| P4    | Policy, approvals, delegation envelope                     | v1-harness  |
| P5    | EA profile, shared assets, first end-to-end user           | v1-harness  |
| P6    | Coding profile, till-done loop, token discipline in-flight | v2-coding   |
| P7    | Adversarial review, teams, pipelines, sub-agents           | v2-coding   |
| P8    | Scheduler, system backup/restore, run recovery, workspace rollback | v2-coding   |
| P9    | Home profile, HA adapters                                  | v3-home     |
| P10   | Reflection, optional surfaces, long-horizon refinements    | v3-home     |

## Epics

- One issue per epic, labeled `epic` plus the relevant phase label.
- Body contains a checklist linking every sub-issue by number.
- Closed when all sub-issues are closed and exit criteria are met.

## Issues

- Title prefix `Pn-k:` (e.g., `P1-3: Health endpoints`) to make phase plus ordering obvious.
- First body line references the parent epic: `Parent epic: #N`.
- Every issue links to the ADRs and specs it implements.
- Use `Depends on: #X` lines for blocking relationships.

## Commits and PRs

See `AGENTS.md` for the branch-per-issue workflow, required completion evidence, and prohibited behaviors. Use the `gh` CLI for all GitHub operations; never launch a browser subagent for GitHub tasks.
