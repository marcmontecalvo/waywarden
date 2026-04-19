# EPIC: <phase-id> <name>

## Goal
<one-paragraph statement of what this phase delivers and why; name the concrete operator-visible or agent-visible outcome>

## Canonical references
- ADRs: <ADR numbers this epic is governed by>
- Specs: <spec ids this epic depends on, e.g. `RT-001`, `RT-002`>
- Prior epics: <#issue-number (title), ...>

## Order of execution
- [ ] <phase-id>-1: <title> (#<issue-number>)
- [ ] <phase-id>-2: <title> (#<issue-number>)
- [ ] <phase-id>-3: <title> (#<issue-number>)

## Sequencing notes
- The checklist order is authoritative for `work-next-issue-in-given-epic`.
- Each child issue's `Blocking dependencies` section is the source of truth for readiness; the checklist order must be consistent with the dependency graph.
- Identify any item whose order differs from its issue number and explain why.

## Global constraints
- <constraint that applies to every child>
- <constraint that applies to every child>

## Definition of done
- Every child issue above is closed.
- <exit criterion proving the epic delivered its outcome>
- <exit criterion proving canonical specs / ADRs are honored>
- CI (Linux + Windows) stays green; 80% coverage gate stays green on the honest denominator.

## Out of scope
- <item intentionally deferred to a later phase>
- <item intentionally deferred to a later phase>
