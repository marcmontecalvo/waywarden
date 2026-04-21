---
type: architecture
title: "ADR 0013: Voice Session Orchestration and Conference Participation"
status: Proposed
date: 2026-04-21
adr_number: "0013"
relates_to: [0001, 0002, 0006, 0010, 0011]
supersedes: null
superseded_by: null
---

# ADR 0013: Voice session orchestration and conference participation

## Status
Proposed

## Problem
WayWarden is expected to support voice-driven use cases later, including:
- direct voice interaction with an EA or other profile
- agent handoff during live sessions
- silent note-taking during calls
- bringing a second profile into a live conversation
- future phone / conferencing style participation

The risk is building voice as a separate subsystem with its own agent model, prompts, memory behavior, and orchestration rules.

That would create:
- duplicated runtime logic
- profile drift between text and voice
- special-case session behavior
- brittle one-off "super voice bot" designs
- hidden coupling between audio transport and agent logic

## Decision
Treat voice as a **session interface over the same harness runtime**, not as a separate agent system.

WayWarden voice support should be built as:
- a voice-facing session layer
- a conversation/session orchestrator
- the shared core agent runtime behind it
- explicit participant roles and handoff rules
- post-session artifact generation through normal harness primitives

Voice is a transport and orchestration concern.
It is not a separate profile architecture.

## Core model

### Voice is a client surface
Voice belongs with other client surfaces such as:
- CLI
- dashboard
- future desktop surface
- future HA-facing control surface

It should sit on top of the same control plane and runtime boundaries described elsewhere.

### One runtime, many participation modes
A profile callable in text should be callable in voice, subject to policy, surface support, and tool constraints.

Examples:
- join as the main conversational participant
- join as a silent note taker
- join as an advisor that only speaks when invoked
- join as a delegated specialist for part of a session

### No "one giant voice agent"
The preferred pattern is:
- a small real-time session conductor at the edge
- specialist agents behind it when needed

The conductor handles turn-taking, interruption, routing, and role-aware handoff.
It should not become the place where all domain behavior lives.

## Session roles
Voice sessions should support explicit participant roles such as:
- primary speaker
- silent observer
- advisor
- note taker
- delegated specialist

These roles are harness-level concepts, not provider-specific tricks.

Each role should carry:
- speaking permissions
- tool permissions
- visibility scope
- memory/write permissions
- artifact permissions

## Session semantics
A voice session should track at least:
- which instance owns the session
- which profile or profiles are participating
- who is speaking
- who the active addressed party is
- whether an agent response is public to the session or private/internal
- which agent, if any, has been handed control
- which artifacts are being created from the session

This should work for:
- one human + one agent
- one human + multiple agents
- multiple humans + one or more agents

## Handoffs
Voice handoff should be a first-class orchestration primitive.

Examples:
- "bring in the EA"
- "have the coding profile listen and advise"
- "add a note taker to this call"
- "escalate this portion to the implementation specialist"

A handoff should not require swapping to a separate runtime model.
It should reuse the same profile, team, delegation, and policy machinery already defined for the harness.

## Boundaries

### 1. Voice gateway
Owns:
- audio input/output
- VAD / turn detection
- streaming STT/TTS integration
- interruption handling
- telephony / conference transport integration when added

Does not own:
- durable task state
- long-term memory policy
- profile definitions
- business logic for orchestration

### 2. Session orchestrator
Owns:
- session state
- participant roster
- role transitions
- public vs private response routing
- handoff control
- artifact triggers

Does not own:
- provider-specific audio transport details
- deep domain logic that belongs in profiles, tools, routines, or policies

### 3. Shared agent runtime
Owns:
- profile execution
- tool invocation
- policy checks
- approvals
- memory and knowledge access
- delegation and sub-agent behavior

Voice uses this runtime.
It does not fork it.

### 4. Artifact pipeline
Owns:
- notes
- summaries
- action items
- follow-up tasks
- calendar or CRM writes when approved
- memory or knowledge writes when explicitly routed there

Post-session outputs should flow through normal artifact and policy pathways, not side channels.

## Implications

### Profile invocation stays unified
"Call the EA" and "spawn the EA in text" should resolve through the same underlying profile/runtime contracts.

### Voice must honor existing policy
Speaking in a live session does not bypass approvals.
If a profile would require approval to send email, write a calendar event, or mutate HA state in text, it should still require approval in voice.

### Real-time edge logic should stay thin
Latency-sensitive behavior belongs in the edge/session conductor only where necessary:
- interruption management
- turn-taking
- barge-in handling
- basic routing

Do not move core harness behavior into the edge just because it is voice.

### Multi-party visibility must be explicit
The harness should distinguish:
- public speech to the whole session
- private scratch or hidden reasoning
- silent artifact generation
- advisor-only responses not yet surfaced aloud

### Voice should compose with future teams/pipelines
Conference participation should later be able to invoke:
- routines
- teams
- pipelines
- delegated specialists
without inventing a second orchestration model just for calls.

## Non-goals
- building a full contact-center product in v1
- making telephony the primary harness architecture
- baking one voice vendor directly into the domain model
- creating a separate voice-only profile system
- letting audio transport dictate task, memory, or policy architecture
- shipping autonomous speaking agents without explicit role and policy controls

## Phased adoption

### Near-term
Capture voice as an architectural concern and keep current ADRs compatible with it.

### Later implementation direction
Likely add:
- voice gateway adapter boundary
- session participant/role model
- public/private response routing contract
- session artifact hooks
- conference/telephony adapters where justified

### Roadmap fit
This is more aligned with later milestones than the first boot slice, but the boundary decisions belong now so text-first implementation does not paint the project into a corner.

## Related
- ADR 0001: context and goals
- ADR 0002: core harness plus profile packs
- ADR 0006: v1 / v2 / v3 roadmap
- ADR 0010: inspiration from other repos
- ADR 0011: harness boundaries and client surfaces
