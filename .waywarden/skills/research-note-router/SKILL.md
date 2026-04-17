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
- before proposing any issue, grep `docs/issues/ordered-issues.md` for existing entries covering the same scope
- before proposing any spec, check `docs/specs/` tree for existing files in adjacent areas
- before proposing any ADR, check `docs/architecture/` for existing ADRs covering the decision space
- verify source_url returns 200 before accepting research claims at face value

# Required pre-flight verification

Before producing any output sections, perform and record these verification steps. Do not skip. Do not infer results from the note text alone.

1. **Source URL check:** Fetch the `source_url` from the note's frontmatter. Record the HTTP status. If it returns 404 or is otherwise inaccessible, flag it — the note's claims about the source are unverified and proprietary/OSS analysis may be wrong.

2. **Issue duplication check:** Read `docs/issues/ordered-issues.md` end-to-end. Grep for keywords from the note's title and key concepts. Record any existing ordered-issue numbers that cover the same scope. If a matching issue exists, route to *enriching that issue*, not creating a new one.

3. **Spec duplication check:** List `docs/specs/` recursively. Identify any existing spec in an adjacent area (same phase, same profile, same capability domain). Record matches by path.

4. **ADR duplication AND scope check:** List `docs/architecture/`. Read full content (not just titles) of:
   - every ADR in the note's `relates_to_adrs`
   - any ADR whose title mentions the note's topic
   - any ADR covering roadmap, extension contracts, or prompt/routine policy (these frequently contain scope commitments that constrain routing)
   Record not just topic matches but also scope commitments (e.g., "ADR 0006 lists X as V2 scope") and implementation-mode constraints (e.g., "ADR 0008 requires routine, not prompt").

5. **Milestone/epic scope check:** Read `docs/issues/milestones.md` and `docs/issues/epics.md`. Record whether the note's topic is already scoped to a specific milestone, epic, or profile. Routing must respect that scope — do not land a profile-specific capability in harness-core, or vice versa.

6. **Convention check:** Inspect 2–3 existing files in each target bucket (`docs/specs/`, `docs/prompts/`, `docs/issues/`) to confirm proposed paths match actual naming and subdirectory patterns. Record the reference files used.

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

## 0.5) Pre-flight Verification Record
Report the results of each required pre-flight check. Do not write "checked" without naming what was checked. If a check could not be performed, say why.

- **Source URL status:** [HTTP status code or "inaccessible — reason"]
- **Ordered-issues matches:** [list of issue numbers + titles, or "none found after grepping for: X, Y, Z"]
- **Existing spec matches:** [list of paths, or "none found in: <paths scanned>"]
- **Existing ADR matches:** [list of ADR numbers + titles, or "none found in <paths scanned>"]
- **Milestone/epic scope:** [milestone/epic ID owning this topic, or "not yet scoped"]
- **Convention reference files:** [2–3 paths used to validate proposed naming]

If any pre-flight check surfaces a match, Section 3 (Routing Decisions) must explicitly address it — either by routing to enrichment of the existing artifact or by justifying why a new one is warranted despite overlap.

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
For each potential ADR, answer:
- Title
- Decision or problem statement
- Conditional trigger: "Promote to ADR IF [specific condition]; otherwise land as spec/issues"
- Why now or why not now

If you propose no ADR, you must state the condition under which one would be warranted. Do not write "none — concepts don't require architectural decisions" without naming the threshold.

### Spec candidates
- title
- scope in 3-5 bullets
- dependencies

### Issue/task candidates
- title
- issue type
- priority
- concrete next action
*Each issue's "concrete next action" must:*
- *Name a specific deliverable (file, matrix, checklist, test fixture)*
- *Include enumerated scope items (categories, count, or named components)*
- *Be executable without further clarification*

*Reject vague verbs alone: "create", "implement", "build". Pair them with what and how many.*

### Prompt candidates
- title
- prompt type
- used by
- purpose

## 5) Cleanup Recommendations For The Research File

For each item below, write a concrete recommendation OR a one-sentence justification for why no change is needed. Do not write "none" alone.

- Frontmatter fixes (check status progression: Captured → Analyzed → Routed):
- Title, status, or tag improvements (propose at least 3 candidate tags or justify why existing tags suffice):
- Bucket placement (research / roadmap / references / archive) with reason:
- Split decision with reason:

## 6) Final Verdict
Choose exactly one:
- Keep as research only
- Keep and enrich
- Keep and graduate to ADR
- Keep and graduate to spec/issues
- Move to roadmap
- Move to references
- Archive / low value

## 7) Self-Critique

Before finalizing, answer:
- Does my Forced Classification match my Final Verdict? If not, fix one.
- Did I propose at least one downstream artifact with a path that follows existing repo conventions (`docs/specs/<area>/<name>.md`, `docs/architecture/NNNN-<name>.md`, `docs/prompts/<role>/<name>.md`)?
- Are my issue actions executable today, or do they require another planning round?
- Did I leave any field blank or write "none" without justification?
- Did my routing decisions incorporate every match surfaced in Section 0.5, or did I propose duplicates? If duplicates, fix Section 3 and Section 4.

## 8) Autonomous Action Execution

After self-critique passes, execute the routing decisions automatically. Do not ask for permission per action — the pre-flight verification and consistency checks are the approval gate.

### Execution order
1. **Update the research note frontmatter** — set `status: Routed`, add/update `relates_to_adrs`, add new tags from Section 5.
2. **Create spec files** proposed in Section 4 as stub files with frontmatter + scope bullets + dependencies + "TODO: fill from research note" body section.
3. **Create prompt files** proposed in Section 4 as stubs with frontmatter + purpose + "TODO: author per spec" body.
4. **Create GitHub issues** via `gh issue create` for every Issue candidate in Section 4, with:
   - title from the candidate
   - body containing: link to research note, link to spec stub (if created), concrete next action verbatim from Section 4
   - labels applied per the labeling rules below
5. **Enrich existing ordered-issues.md entries** if Section 0.5 found matches — append acceptance criteria under the existing numbered item, do not renumber.
6. **Emit an execution report** as the final response section listing every file created, every issue created (with URL), every file modified.

### Labeling rules for `gh issue create`

Every issue must get exactly one label from each of these three axes:

**Priority axis** (when to work on it):
- `now` — blocks current milestone; pick up next
- `next` — should land this milestone but not blocking
- `soon` — next milestone
- `later` — future milestone, keep in backlog
- `whenever` — nice-to-have, no milestone commitment

**Status axis** (can it be worked on now):
- `ready` — all dependencies met, executable today
- `blocked` — waiting on another issue; use `blocked-by:#N` in body
- `spike` — needs investigation before estimate is possible
- `design` — needs spec/ADR before implementation

**Scope axis** (what subsystem):
- `harness-core`
- `profile-ea`
- `profile-coding`
- `profile-home`
- `policy-approvals`
- `memory-knowledge`
- `extensions`
- `ops`
- `docs`

### Milestone assignment

If Section 0.5 surfaced a milestone match (E/M number), attach `--milestone "v1-harness"` (or appropriate milestone). If no milestone match, omit the flag — the issue lands in the global backlog.

### Pre-execution gate

If any of the following are true, STOP and report instead of executing:
- Section 0.5 reported an inaccessible source URL AND the final verdict depends on the source's claims
- Duplication check found an exact-match issue with identical scope (enrichment only, no new issue)
- Classification is `redundant/low-value` (archive only, no artifacts)
- Classification is `reference-only` (move file, no other artifacts)

# Consistency check (must pass before returning)

- If Forced Classification is `architecture-driving`, Final Verdict must be `Keep and graduate to ADR` or include an ADR candidate.
- If Forced Classification is `spec-driving` or `implementation-driving`, Final Verdict must be `Keep and graduate to spec/issues` and Section 4 must contain at least one Spec or Issue candidate.
- If Forced Classification is `roadmap-only`, Final Verdict must be `Move to roadmap`.
- If Forced Classification is `reference-only`, Final Verdict must be `Move to references`.
- If Forced Classification is `redundant/low-value`, Final Verdict must be `Archive / low value`.
- If any candidate is omitted, the rationale must appear in that section, not be left blank or "none".
- If Forced Classification is `prompt/behavior-driving`, Final Verdict must be `Keep and graduate to spec/issues` (prompts ship via issues) or `Keep and enrich` if prompts already exist.
- Section 0.5 must be fully populated. Any "checked" entry without specifics (file paths, issue numbers, HTTP status) fails the check.
- If Section 0.5 reports an ordered-issues match, Section 4's Issue candidates must reference that existing issue number, not propose a duplicate.
- If Section 0.5 reports an existing spec match, Section 3 must either route to enrichment of that spec or justify the new spec in Section 4's Spec candidates.

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

# Worked example

The following demonstrates the expected quality bar. Use it as a pattern reference for specificity, conditional reasoning, and concreteness.

## Example input

A research note at `docs/research/langgraph-checkpointing.md` covering LangGraph's checkpoint/resume system, with frontmatter `status: Captured`, `tags: [agents, state, persistence]`, `relates_to_adrs: []`, source pointing to LangGraph's checkpointing docs.

## Example output

### 0) Forced Classification
spec-driving

### 1) Research Note Assessment
- File: langgraph-checkpointing.md
- Current status: Captured
- Keep in research? yes
- Best bucket: research, with downstream routing into spec and issues
- Relevance now: High
- Implementation readiness: Medium
- Duplication risk: Medium — overlaps with existing session-state work in `docs/specs/runtime/session-persistence.md`
- Confidence: 7

### 2) Core Extracted Signals
#### Strong ideas worth keeping
- Checkpoint-after-each-node pattern that allows resume from arbitrary step without replaying tool calls
- Pluggable checkpoint backend (memory, SQLite, Postgres) decoupled from agent definition
- Thread-scoped state isolation with explicit thread_id parameter

#### Why they matter for WayWarden
- Long-running EA workflows currently lose state on harness restart; checkpoint-per-node would survive crashes mid-execution
- Pluggable backend matches WayWarden's runtime-separation model — checkpoint store can live in a different runtime than the agent
- Thread isolation maps directly to per-conversation approval scopes

#### What to borrow
- Checkpoint-after-node hook in the harness execution loop
- Backend interface abstraction (write/read/list/delete by thread_id)
- Resume-from-checkpoint as an explicit operator action, not automatic

#### What to avoid
- LangGraph's full graph-DSL for defining flows — WayWarden's existing planner is sufficient
- Automatic resume on every restart — operator should explicitly choose to resume vs. restart
- Checkpointing tool-call results that contain sensitive data without redaction

#### Proprietary-only / not portable
- LangGraph's LangSmith integration for checkpoint visualization is proprietary; WayWarden would need its own inspection UI

#### Closest OSS path
- Implement a minimal `CheckpointStore` interface in the harness, with SQLite default backend
- Use the LangGraph checkpoint schema as a reference for what fields to persist (state, next, metadata, parent_config)

### 3) Routing Decisions
- Target doc type: spec
- Proposed path: `docs/specs/runtime/checkpoint-and-resume.md`
- Proposed title: `Harness Checkpoint and Resume`
- Why this should exist: Runtime crash recovery and operator-initiated resume are not covered in existing specs; this concretizes the contract before implementation
- Source research sections supporting it: "Checkpoint-after-each-node pattern", "Pluggable checkpoint backend", "What to borrow"

- Target doc type: issue
- Proposed path: tracked in issue tracker, no doc file
- Proposed title: `Define CheckpointStore interface and ship SQLite backend`
- Why this should exist: The interface design is concrete enough to start without waiting on the full spec; spec and code can land together
- Source research sections supporting it: "Pluggable checkpoint backend", "Closest OSS path"

### 4) Proposed Graduations
#### ADR candidates
- Title: `ADR 0014: Harness state persistence model`
- Decision or problem statement: Whether the harness owns checkpoint storage and resume semantics, or delegates to individual agents
- Conditional trigger: Promote to ADR IF checkpoint storage will be a harness-level invariant that all agents must conform to; otherwise land as spec only
- Why now or why not now: Now, if the team agrees this is a harness contract. The runtime-separation model already implies harness-owned state, so the ADR mostly codifies an existing direction.

#### Spec candidates
- Title: `Harness Checkpoint and Resume`
- Scope:
  - Define `CheckpointStore` interface (write, read, list_by_thread, delete_by_thread)
  - Define checkpoint trigger points in the execution loop (after each node, on approval boundary, on error)
  - Define resume semantics: full replay vs. state-only restore
  - Define redaction rules for sensitive tool-call results before persistence
  - Define operator commands for list/inspect/resume/discard
- Dependencies:
  - `docs/architecture/0003-runtime-separation.md`
  - existing approval boundary spec
  - tool policy / destructive-action policy

#### Issue/task candidates
- Title: `Define CheckpointStore interface and ship SQLite backend`
- Issue type: feature
- Priority: high
- Concrete next action: Author `harness/checkpoint/store.py` with the 4-method interface (write, read, list_by_thread, delete_by_thread) and a SQLite implementation covering 3 tables (checkpoints, threads, metadata). Include integration test fixture with 5 scenarios: write-read roundtrip, list by thread, delete cascade, concurrent writes to same thread, missing thread read.

- Title: `Add checkpoint hook to harness execution loop`
- Issue type: feature
- Priority: medium
- Concrete next action: Modify `harness/executor.py` to call `CheckpointStore.write()` after each node completion, gated by a `checkpoint_enabled` flag in harness config. Add 4 unit tests covering: hook fires on success, hook skipped when disabled, hook failure does not block execution, hook receives correct thread_id.

#### Prompt candidates
- No prompt candidates. This is infrastructure, not a behavior change. Prompts would only be warranted if we add an operator-facing resume confirmation flow, which is out of scope for the initial spec.

### 5) Cleanup Recommendations For The Research File
- Frontmatter fixes: Update `status` from `Captured` to `Analyzed` once routing is accepted. Add `relates_to_adrs: [0003, 0014]` (0014 pending creation).
- Title, status, or tag improvements: Existing tags are too generic. Add `checkpointing`, `resume`, `runtime-recovery` to improve discoverability against future state-management research.
- Bucket placement: Stay in `docs/research/`. Promote sections to spec rather than moving the file — original context is still valuable for future reviewers.
- Split decision: No split. Single coherent topic.

### 6) Final Verdict
Keep and graduate to spec/issues

### 7) Self-Critique
- Forced Classification (`spec-driving`) matches Final Verdict (`Keep and graduate to spec/issues`). Consistent.
- Proposed paths follow conventions: `docs/specs/runtime/checkpoint-and-resume.md`, `docs/architecture/0014-...`. Confirmed.
- Issue actions are executable today — both name specific files, method counts, and test scenario counts.
- No blank fields. Prompt candidates section explicitly justifies the omission rather than writing "none".
- Duplication risk flagged in Section 1 should be resolved before spec is written: review `docs/specs/runtime/session-persistence.md` for overlap.

### 8) Autonomous Action Execution

EXECUTION COMPLETE

Files created:
- docs/specs/runtime/checkpoint-and-resume.md (stub with frontmatter, scope bullets, dependencies, TODO body)
- docs/architecture/0014-harness-state-persistence-model.md (stub — pending team confirmation per conditional ADR trigger)

Files modified:
- docs/research/langgraph-checkpointing.md (status: Captured → Routed; added tags: checkpointing, resume, runtime-recovery; added relates_to_adrs: [0003])

Issues created:
- #47 Define CheckpointStore interface and ship SQLite backend (https://github.com/marcmontecalvo/waywarden/issues/47) [labels: now, ready, harness-core] [milestone: v1-harness]
- #48 Add checkpoint hook to harness execution loop (https://github.com/marcmontecalvo/waywarden/issues/48) [labels: next, blocked, harness-core] [milestone: v1-harness] [blocked-by: #47]

Enriched:
- None (pre-flight found no ordered-issues.md match)

Skipped:
- Prompt candidate (explicitly declined in Section 4 — not applicable for infrastructure)

Next suggested action: Pick up #47 — labeled `now` + `ready`, no blockers, all dependencies met.