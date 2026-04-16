# Harness Design for Long-Running Apps

Source reference:
- Anthropic engineering article: `harness-design-long-running-apps`

## Note on confidence

This doc is being added as a **design-reference placeholder** based on the article title and the clear relevance of the topic.
It should be revisited with a full source review before being used as the basis for any architecture decision.

## Why it is interesting

WayWarden is explicitly being designed as a **long-running application**, not a disposable single-turn wrapper.
That makes this reference highly relevant at the architectural level.

## Why the topic matters for WayWarden

Long-running agent systems have very different needs from short-lived prompt wrappers:
- explicit state management
- resumability
- background work separation
- approval checkpoints
- failure recovery
- memory and knowledge boundaries
- observability over time

Those concerns are central to WayWarden.

## Likely themes worth extracting

Based on the topic alone, the most relevant design themes are:

### 1. Durable state over chat-state illusion
WayWarden should keep treating persistent state as a real system concern:
- sessions
- tasks
- artifacts
- approvals
- routines
- memory references

### 2. Separation of hot path vs background work
This already aligns with the repo direction:
- user-facing work should stay responsive
- reflection/consolidation/summarization should stay out of the hot path
- long-running jobs should be explicit and inspectable

### 3. Resumability and recovery
A long-running harness needs clean recovery after:
- crashes
- restarts
- partial tool failure
- model failure
- interrupted operator sessions

### 4. Observability and operator trust
A long-running system must make it easy to answer:
- what is it doing?
- what did it already do?
- what is waiting for approval?
- what failed?
- what can be retried?

### 5. Boundaries and governance
The longer a system runs, the more important it is to preserve:
- permission boundaries
- policy enforcement
- identity stability
- non-self-modifying governance rules

## What WayWarden should borrow

Treat this reference as reinforcing architectural priorities around:
- durable task and artifact state
- explicit workflow stages
- background-job discipline
- recovery-friendly execution
- approval-aware orchestration
- strong observability

## What not to copy

- Any provider-specific assumptions
- Any design patterns that make the system opaque or difficult to self-host
- Any architecture that collapses runtime boundaries between EA, coding, and HA concerns

## Best next step

Revisit this doc later with a proper source-backed review and convert any real takeaways into:
- an ADR
- a phased issue doc
- or a concrete runtime design note

## Relevance to WayWarden

Very high.
Even without full source extraction yet, the topic is directly aligned with the kind of system this repo is trying to build.
