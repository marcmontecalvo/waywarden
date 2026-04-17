---
type: research
title: "Documentation Map and Navigation"
status: Active
date: 2026-04-17
source_url: null
source_type: index
priority: directly-relevant
tags: [navigation, structure, metadata]
relates_to_adrs: null
---

# Docs map

This docs tree is split by **intent**, not by age.

**Key reference**: All documents must include [YAML frontmatter](./FRONTMATTER-SPEC.md) with metadata for discovery and linking.

## Folders

- `architecture/`
  - Canonical architecture decisions (ADRs)
  - Durable constraints, boundaries, and design rules
  - If a note changes how WayWarden should actually be built, it should end up here

- `issues/`
  - Execution backlog and phased implementation work
  - What the coding agent should build, in what order
  - Should reference ADRs rather than restating architecture from scratch

- `prompts/`
  - Prompt assets for coding agents and bootstrap flows
  - Prompt docs support execution; they are not the source of truth for system design

- `research/`
  - External products, repos, articles, and UX references
  - Pattern-oriented notes only
  - Useful for fast-moving market inputs before they graduate into architecture decisions

## Usage rules

1. Put **durable decisions** in `architecture/`.
2. Put **fast-moving external observations** in `research/`.
3. Put **build order and implementation work** in `issues/`.
4. Put **execution prompts** in `prompts/`.
5. If a research note changes the actual design, add or update an ADR instead of letting the research doc become the spec.
6. **All documents must include YAML frontmatter** with metadata (type, title, status, date). See [FRONTMATTER-SPEC.md](./FRONTMATTER-SPEC.md) for the standard.

## Working rule for the current phase

WayWarden is still pre-build. That means:
- `research/` will change quickly
- `architecture/` should stay tighter and more stable
- `issues/` should lag architecture slightly and only contain work that is ready to build

## Current risk to avoid

Do not let `research/` become a second architecture folder.

When a new article, repo, or product matters, do this in order:
1. capture it in `research/`
2. extract only the durable implications
3. write or update an ADR
4. only then update the phased backlog in `issues/`
