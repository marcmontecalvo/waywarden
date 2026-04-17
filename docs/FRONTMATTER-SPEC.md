---
type: spec
title: "Documentation Frontmatter Specification"
status: In Use
date: 2026-04-17
spec_number: "DOC-SPEC-001"
phase: harness-core
relates_to_adrs: null
tags: [documentation, metadata, specification]
---

# Documentation Frontmatter Standard

## Purpose
Frontmatter provides structured metadata for all docs, enabling discovery, filtering, linking, and change tracking without reading the full content.

## Format
YAML frontmatter at the top of every `.md` file, enclosed in triple dashes:

```yaml
---
type: architecture | research | spec | issue | prompt
title: "Human-readable title"
status: Proposed | Accepted | Deprecated | Draft | In Progress | Ready
date: YYYY-MM-DD
author: name or team
---
```

## Fields by Document Type

### All Documents (Required)
- **type**: One of: `architecture`, `research`, `spec`, `issue`, `prompt`
- **title**: Clear, descriptive title (max 80 chars)
- **status**: Current state (see allowed values per type below)
- **date**: ISO 8601 creation or last significant update date

### Architecture (ADRs)
```yaml
type: architecture
title: "ADR 0012: Hooks and Events System"
status: Proposed | Accepted | Deprecated | Superseded
date: 2026-04-17
author: team or individual
adr_number: "0012"
relates_to: [0004, 0005, 0011]  # other ADRs
supersedes: null  # if this replaces a previous ADR
superseded_by: null  # if this has been replaced
```

**Status values**: Proposed (under discussion), Accepted (decided), Deprecated (no longer relevant), Superseded (replaced by another ADR)

**Additional fields**:
- `adr_number`: ADR numbering for easy reference
- `relates_to`: List of related ADR numbers
- `supersedes`: ADR number this replaces
- `superseded_by`: ADR number that replaced this

---

### Research
```yaml
type: research
title: "Pi vs Claude Code — Harness Patterns & Gaps for WayWarden"
status: Captured | Analyzed | Graduating to ADR
date: 2026-04-17
author: researcher name (optional)
source_url: "https://github.com/disler/pi-vs-claude-code"
source_type: repo | product | article | conference-talk | whitepaper
priority: directly-relevant | roadmap | future-reference
tags: [hooks, extensions, multi-agent, open-source]
relates_to_adrs: [0004, 0005, 0011]  # which architecture docs does this inform?
```

**Status values**: Captured (just added), Analyzed (reviewed for applicability), Graduating to ADR (implication clear, ready for architecture doc)

**Additional fields**:
- `source_url`: Link to the original source material
- `source_type`: Category of source for filtering
- `priority`: Is this directly relevant now or future-roadmap?
- `tags`: Keywords for discovery (hooks, extensions, safety, UI, orchestration, etc.)
- `relates_to_adrs`: Which ADRs does this research inform or challenge?

---

### Spec (Implementation Specifications)
```yaml
type: spec
title: "Hooks and Events System"
status: Draft | In Progress | Ready for Build | Building | Complete
date: 2026-04-17
author: designer name
spec_number: "HS-001"  # optional: internal spec numbering
phase: harness-core | profile-ea | profile-coding | profile-home | backlog
relates_to_adrs: [0012, 0011]
depends_on: [HS-002, 0005-approval-model]  # other specs or ADRs this requires
owner: team or individual responsible
target_milestone: "v1-harness" or null if TBD
```

**Status values**: Draft (rough), In Progress (being refined), Ready for Build (implementation can start), Building (actively implemented), Complete (done)

**Additional fields**:
- `spec_number`: Internal numbering for cross-reference
- `phase`: Which phase of WayWarden does this belong to?
- `relates_to_adrs`: Which architecture decisions does this implement?
- `depends_on`: List of specs or ADRs this spec requires
- `owner`: Who is responsible for this spec?
- `target_milestone`: Which release/phase should this ship in?

---

### Issue (Backlog & Tasks)
```yaml
type: issue
title: "Implement input interception hook for approval gates"
status: Backlog | Planned | In Progress | Done | Blocked
date: 2026-04-17
issue_number: "WW-247"  # optional: issue tracker ID
issue_type: epic | feature | task | bug | spike | design
phase: harness-core | profile-ea | profile-coding | profile-home | backlog
priority: critical | high | medium | low
relates_to_adrs: [0012]
relates_to_specs: [HS-001]
depends_on: [WW-101, WW-203]  # other issues this depends on
owner: assignee or team
estimate: "8h" or "3d" or null if TBD
```

**Status values**: Backlog (not scheduled), Planned (scheduled for upcoming phase), In Progress (currently being worked), Done (completed), Blocked (waiting on something)

**Additional fields**:
- `issue_number`: Tracker ID (GitHub, Jira, Linear, etc.)
- `issue_type`: Category for filtering (epic, feature, task, bug, spike, design)
- `phase`: Which phase does this ship in?
- `priority`: Urgency relative to other work
- `relates_to_adrs`: Which ADRs does this implement?
- `relates_to_specs`: Which specs does this use?
- `depends_on`: Blocking issues or specs
- `owner`: Who is working on this?
- `estimate`: Time estimate if available

---

### Prompt (System Prompts, Specialist Personas, Tool Descriptions)
```yaml
type: prompt
title: "Purpose Gate Extension — Intent Injection"
status: Draft | In Use | Deprecated
date: 2026-04-17
author: prompt engineer name
prompt_type: system-prompt | specialist-persona | tool-description | skill-spec | guard-prompt
used_by: [purpose-gate-extension, ci-agent]  # which agents or extensions use this?
relates_to_adrs: [0012]
relates_to_specs: [HS-001]
version: "1.0"
tags: [intent, approval, input-interception]
```

**Status values**: Draft (new), In Use (active), Deprecated (no longer used), Archived

**Additional fields**:
- `prompt_type`: What kind of prompt is this?
- `used_by`: Which agents, extensions, or systems consume this?
- `relates_to_adrs`: Which architecture decisions does this support?
- `relates_to_specs`: Which specs does this implement?
- `version`: Semantic version for tracking changes
- `tags`: Keywords (intent, safety, routing, etc.)

---

## Minimal Frontmatter (for documents without full metadata)

If you're unsure about all fields, include at minimum:
```yaml
type: [document type]
title: "Clear title"
status: [appropriate status]
date: YYYY-MM-DD
```

All other fields are optional and should be added as they become relevant.

---

## Usage Rules

1. **All new documents must include frontmatter** with at least the 4 required fields above.

2. **Use consistent field names** — do not invent new fields without updating this spec first.

3. **Keep frontmatter lean** — include only fields that have a value or clear relevance.

4. **Use YAML arrays for lists**:
   ```yaml
   relates_to: [0004, 0005, 0011]
   tags: [hooks, extensions, safety]
   ```

5. **Link strategically**:
   - `relates_to_adrs`: Use this to show which architecture decisions a document informs or depends on
   - `depends_on`: Use this to show blocking relationships
   - `used_by`: Use this to show what uses a prompt or spec

6. **Status transitions**:
   - Research starts as `Captured`, may graduate to `Analyzed`, then becomes `Graduating to ADR`
   - When a research doc changes architecture, create/update an ADR and mark the research as `Graduating to ADR`
   - Issues move: `Backlog` → `Planned` → `In Progress` → `Done`
   - Specs move: `Draft` → `In Progress` → `Ready for Build` → `Building` → `Complete`

7. **Dates**: Update `date` field only when the document's substance significantly changes. Don't update for minor typo fixes.

8. **Authors**: Optional but recommended for accountability and questions. Use name or team name.

---

## Example: Architecture ADR with Full Frontmatter

```yaml
---
type: architecture
title: "ADR 0012: Hooks and Events System"
status: Proposed
date: 2026-04-17
author: Marc M.
adr_number: "0012"
relates_to: [0004, 0005, 0011]
supersedes: null
superseded_by: null
---

# ADR 0012: Hooks and Events System

## Status
Proposed

## Problem
[rest of ADR content...]
```

---

## Example: Research Document with Full Frontmatter

```yaml
---
type: research
title: "Pi vs Claude Code — Harness Patterns & Gaps for WayWarden"
status: Analyzed
date: 2026-04-17
source_url: "https://github.com/disler/pi-vs-claude-code"
source_type: repo
priority: directly-relevant
tags: [hooks, extensions, multi-agent, open-source, safety]
relates_to_adrs: [0004, 0005, 0011]
---

# Pi vs Claude Code — Harness Patterns & Gaps for WayWarden

**Source**: https://github.com/disler/pi-vs-claude-code

[rest of document...]
```

---

## Example: Spec with Full Frontmatter

```yaml
---
type: spec
title: "Hooks and Events System"
status: Draft
date: 2026-04-17
author: Architecture team
spec_number: "HS-001"
phase: harness-core
relates_to_adrs: [0012, 0011]
depends_on: [0005-approval-model]
owner: TBD
target_milestone: "v1-harness"
---

# Hooks and Events System Specification

## Overview
[specification content...]
```

---

## Tooling & Discovery

This frontmatter enables:
1. **Automated linking**: Scripts can find related docs via `relates_to_adrs`, `depends_on`, etc.
2. **Status dashboards**: See at a glance what's Proposed vs Accepted vs Ready for Build
3. **Research-to-ADR tracking**: See which research docs are graduating to architecture
4. **Phase filtering**: Show only docs relevant to current build phase
5. **Dependency analysis**: Understand what blocks what
6. **Change tracking**: See when documents were last updated
