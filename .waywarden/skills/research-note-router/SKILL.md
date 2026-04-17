---
name: research-note-router
description: Triage a docs/research markdown note, extract reusable signals, and route outputs into ADR, spec, issue, prompt, roadmap, or reference buckets
---

# Purpose

Process a single `docs/research/*.md` file as an **extraction-and-routing task** rather than a generic summary task.

This skill exists to help WayWarden turn research notes into actionable downstream planning artifacts without treating external products, repos, or articles as the product spec.

# Use this skill when

Use this skill when all or most of the following are true:
- The source file lives in `docs/research/`
- The note is about an external product, repo, article, UX pattern, or architecture pattern
- The real goal is to decide what WayWarden should keep, borrow, ignore, graduate, or re-bucket
- You need structured outputs that can become ADRs, specs, prompts, issues, roadmap items, or references

# Do not use this skill when

Do **not** use this skill when:
- The file is already an ADR, implementation spec, issue doc, or prompt doc
- The task is only to rewrite prose for clarity
- The task is broad repo cleanup with no specific research note input
- The source material is not yet captured in markdown and first needs transcription or source extraction

# Core operating rules

1. Do not treat any external product, article, repo, or company as the spec.
2. Pull over patterns, not branding, copy, or surface mimicry.
3. Prefer insights that reduce token bloat, reduce operator friction, improve safety, or fit WayWarden's architecture.
4. Call out proprietary-only advantages that are not realistically portable.
5. Prefer OSS implementation paths where they can get most of the value.
6. Be strict. Weak, redundant, or speculative notes should not be forced into downstream docs.
7. If the research materially changes how WayWarden should be built, flag it for graduation into `docs/architecture/`.
8. If the note is mostly a future idea bank, move it toward roadmap instead of pretending it is implementation-ready.
9. If the note is mostly a pointer to an external repo or artifact, consider `docs/references/` instead of `docs/research/`.

# Inputs

Minimum expected input:
- One research markdown file from `docs/research/`

Useful supporting context when available:
- `docs/research/README.md`
- `docs/FRONTMATTER-SPEC.md`
- related ADRs in `docs/architecture/`
- related specs or prompts already present in the repo

# Required checks

Before producing output, check the following:
- frontmatter validity
- title quality
- status appropriateness
- priority appropriateness
- presence of `source_url`
- tag quality
- whether `relates_to_adrs` is empty but should not be
- whether the content belongs in research at all

# Required extraction questions

For the given research note, answer all of these:
- What is actually strong here?
- Why does it matter for WayWarden?
- What should WayWarden borrow?
- What should WayWarden explicitly avoid?
- What is proprietary-only or not portable?
- Is there an OSS path that gets most of the value?
- Does this belong in research, roadmap, references, or should it graduate?
- Does this create an ADR candidate, spec candidate, issue candidate, or prompt candidate?

# Required output format

Always return results in this exact structure.

## 0) Forced Classification
Choose exactly one primary class:
- architecture-driving
- spec-driving
- implementation-driving
- prompt/behavior-driving
- roadmap-only
- reference-only
- redundant/low-value

## 1) Research Note Assessment
- File:
- Current status:
- Keep in research? yes/no
- Best bucket:
- Relevance now: High / Medium / Low
- Implementation readiness: High / Medium / Low
- Duplication risk: High / Medium / Low
- Confidence: 1-10

## 2) Core Extracted Signals
### Strong ideas worth keeping
- ...

### Why they matter for WayWarden
- ...

### What to borrow
- ...

### What to avoid
- ...

### Proprietary-only / not portable
- ...

### Closest OSS path
- ...

## 3) Routing Decisions
For each downstream output candidate, provide:
- Target doc type: architecture | spec | issue | prompt | roadmap | reference
- Proposed path:
- Proposed title:
- Why this should exist:
- Source research sections supporting it:

If no downstream item should be created, say so explicitly.

## 4) Proposed Graduations
### ADR candidates
- title
- decision or problem statement
- why now or why not now

### Spec candidates
- title
- scope in 3-5 bullets
- dependencies

### Issue/task candidates
- title
- issue type
- priority
- concrete next action

### Prompt candidates
- title
- prompt type
- used by
- purpose

## 5) Cleanup Recommendations For The Research File
- frontmatter fixes needed
- title, status, or tag improvements
- whether the file should stay where it is, move to roadmap, move to references, or be archived
- whether the file should be split

## 6) Final Verdict
Choose exactly one:
- Keep as research only
- Keep and enrich
- Keep and graduate to ADR
- Keep and graduate to spec/issues
- Move to roadmap
- Move to references
- Archive / low value

# Execution guidance

When applying this skill:
- Be concise but concrete.
- Prefer exact proposed file paths.
- Prefer file names that match existing repo naming conventions.
- Do not generate fake precision. If a downstream artifact is premature, say so.
- If a note has only one real reusable insight, output one strong route instead of five weak ones.

# Antigravity invocation hint

Use this skill when the operator asks for any of the following:
- process this research note
- triage this docs/research file
- route this research into ADR/spec/issues
- decide what bucket this research belongs in
- extract build-worthy ideas from this research note

# Recommended operator prompt

```text
Use the research-note-router skill on this file:

[path or pasted markdown]

Also use these supporting docs if needed:
- docs/research/README.md
- docs/FRONTMATTER-SPEC.md

Return the exact skill output format and be strict about routing decisions.
```

# Future enhancement ideas

- Add a companion script that scans all `docs/research/*.md` files and produces a routing matrix
- Add a generator that can optionally emit first-draft ADR/spec/issue docs from approved routing outputs
- Add duplicate detection against existing ADR/spec titles before proposing new downstream docs
