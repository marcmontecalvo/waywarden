---
type: architecture
title: "ADR 0013: Voice Session Orchestration, Identity, and Conference Participation"
status: Proposed
date: 2026-04-21
adr_number: "0013"
relates_to: [0001, 0002, 0005, 0006, 0010, 0011]
supersedes: null
superseded_by: null
---

# ADR 0013: Voice session orchestration, identity, and conference participation

## Status
Proposed

## Problem
WayWarden is expected to support voice-driven use cases later, including:
- direct voice interaction with an EA or other profile
- wake-word activation in the home
- voice-based user identification and authorization
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

A second risk is treating multi-party voice as only an agent-orchestration problem.

Once the harness supports:
- multiple humans
- private vs public responses
- approvals
- downstream writes to memory, tasks, calendars, CRM, or home systems

then the trust boundary depends on an explicit model of:
- which human principal is present
- how that principal was authenticated
- what that principal is allowed to hear
- what that principal is allowed to approve or invoke
- when that principal joined, left, or changed state in the session

Without that model, private routing, conference participation, and approval-bearing voice flows are not trustworthy.

## Decision
Treat voice as a **session interface over the same harness runtime**, not as a separate agent system.

WayWarden voice support should be built as:
- a voice-facing session layer
- a conversation/session orchestrator
- the shared core agent runtime behind it
- explicit human and agent participant roles
- explicit identity, authorization, and audience-binding rules
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
A profile callable in text should be callable in voice, subject to policy, surface support, participant identity, and tool constraints.

Examples:
- join as the main conversational participant
- join as a silent note taker
- join as an advisor that only speaks when invoked
- join as a delegated specialist for part of a session

### No "one giant voice agent"
The preferred pattern is:
- a small real-time session conductor at the edge
- specialist agents behind it when needed

The conductor handles turn-taking, interruption, routing, identity-aware policy checks, and role-aware handoff.
It should not become the place where all domain behavior lives.

## Participant model

### Human principals are first-class
A voice session must model humans explicitly, not just agents and profiles.

A human participant should carry at least:
- participant id
- principal id if known
- display name
- authentication state
- authentication method
- authorization scopes
- current audience membership
- current speaking state
- join time
- leave time if applicable
- whether approval authority is permitted in this session

Authentication state may be:
- anonymous
- claimed
- partially verified
- verified

Authentication method may include:
- authenticated web session
- device-bound trust
- wake-word/device context
- voice print
- telephony identity
- manual operator confirmation

### Agent participants are also first-class
An agent participant should carry at least:
- participant id
- instance id
- profile id
- role
- speaking permissions
- tool permissions
- visibility scope
- memory/write permissions
- artifact permissions

### Roles are not enough without scope
Voice roles such as:
- primary speaker
- silent observer
- advisor
- note taker
- delegated specialist

must be paired with explicit scope rules for:
- who can hear the participant
- who can address the participant
- which outputs are public
- which outputs are private
- which approvals the participant can request or receive

## Session semantics
A voice session should track at least:
- which instance owns the session
- which transport or entry surface created it
- all human participants
- all agent participants
- join/leave events
- authentication state transitions
- active speaker
- active addressed party
- current audience bindings
- whether a response is public to the whole session, scoped to a subset, or private/internal
- which agent, if any, has been handed control
- which artifacts are being created from the session
- which approvals were requested, by whom, and under what authority
- which downstream writes were proposed, approved, denied, or deferred

This should work for:
- one human + one agent
- one human + multiple agents
- multiple humans + one or more agents

## Audience binding and private routing
Private or scoped responses must bind to an explicit audience.

The orchestrator must know:
- which participants are in the audience
- why they are allowed in that audience
- whether the scoped response may be spoken aloud, rendered in a private client surface, or stored only as an internal artifact

Examples:
- advisor-only response visible to Marc but not to other humans on the call
- note-taker output stored as an artifact and not spoken aloud
- approval request visible only to a verified principal with the required authority
- family-agent invocation allowed only when the current speaker is authenticated strongly enough

No private routing should rely on vague notions like "the current user" once multi-party sessions exist.

## Approvals and downstream authority
Voice does not bypass policy.

Any approval-bearing action such as:
- send email
- edit calendar
- write CRM
- write memory
- write knowledge
- mutate Home Assistant state
- place or bridge a phone call

must bind to:
- a specific authenticated or sufficiently verified human principal
- the authorization scope that permits the action
- a session event showing how approval was obtained

For ambiguous or weakly authenticated situations, the system should downgrade to:
- read-only behavior
- deferred task creation
- explicit out-of-band approval
- "I can prepare this, but not execute it yet"

## Handoffs
Voice handoff should be a first-class orchestration primitive.

Examples:
- "bring in the EA"
- "have the coding profile listen and advise"
- "add a note taker to this call"
- "escalate this portion to the implementation specialist"
- "bring in Lisa's agent"

A handoff should not require swapping to a separate runtime model.
It should reuse the same profile, team, delegation, and policy machinery already defined for the harness.

Handoffs that cross user boundaries must also pass identity and policy checks.

## Boundaries

### 1. Voice gateway
Owns:
- audio input/output
- wake-word integration
- VAD / turn detection
- streaming STT/TTS integration
- interruption handling
- telephony / conference transport integration when added
- device/session attachment metadata

Does not own:
- durable task state
- long-term memory policy
- profile definitions
- business logic for orchestration
- final authorization decisions

### 2. Session orchestrator
Owns:
- session state
- participant roster
- role transitions
- join/leave tracking
- identity state transitions
- public vs private response routing
- audience binding
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

## Home and household direction
The first real voice MVP is not a general call-center surface.
It is a controlled home/desk flow.

Planned early direction:
- a basic webpage where the operator selects STT, LLM, and TTS and manually starts a live chat
- a wake-word-driven desk unit using an ESP32-based microphone in the office
- agent speech routed back through a Google Nest Mini exposed through Home Assistant, with room to swap output hardware later if latency is unacceptable
- user voice printing for Marc for identity and authorization
- later additional household users such as Lisa and the kids
- later support for different wake words that target different agents or agent-owned contexts

This progression means the identity model must exist before the more advanced family, phone, and conference stages, even if the first manual webpage flow can begin in a simpler operator-trusted mode.

## Phased goals

### Phase 1
Basic live webpage chat.
- manually start a live session from a web page
- choose STT model
- choose LLM
- choose TTS
- single-user operator-trusted flow
- no complex conferencing required

### Phase 2
Wake-word desk MVP.
- ESP32-based mic in the office
- one wake-word path
- response playback through Home Assistant media player or a lower-latency replacement
- session creation from device + room context

### Phase 3
Voice identity for Marc.
- enroll voice print
- authenticate Marc in-session
- use authenticated identity to unlock higher-trust actions

### Phase 4
Additional household users.
- enroll Lisa and the kids
- support per-user identity, authorization, and context
- maintain explicit fallback behavior when speaker confidence is too low

### Phase 5
Wake-word-to-agent targeting.
- support different wake words or equivalent targeting so different household agents can be invoked directly
- preserve per-agent context, persona, and authorization boundaries

### Phase 6
Phone calls into the agent.
- attach telephony transport
- map call participants into the same participant and identity model
- keep approvals constrained by authentication strength

### Phase 7
Conference calls with humans.
- support multiple human participants on a single session
- require explicit audience binding and scoped/private routing rules

### Phase 8
Conference in agents.
- allow one or more agent participants on the same live call
- support silent observer, advisor, and speaking roles without creating a separate orchestration system

## Implications

### Profile invocation stays unified
"Call the EA" and "spawn the EA in text" should resolve through the same underlying profile/runtime contracts.

### Human identity must be explicit before private routing is trusted
Private routing, scoped approvals, and multi-party conference participation depend on explicit principal modeling.
Do not ship those features on top of an implicit "current user" abstraction.

### Voice must honor existing policy
Speaking in a live session does not bypass approvals.
If a profile would require approval to send email, write a calendar event, or mutate HA state in text, it should still require approval in voice.

### Real-time edge logic should stay thin
Latency-sensitive behavior belongs in the edge/session conductor only where necessary:
- interruption management
- turn-taking
- barge-in handling
- basic routing
- identity signal collection

Do not move core harness behavior into the edge just because it is voice.

### Multi-party visibility must be explicit
The harness should distinguish:
- public speech to the whole session
- scoped speech to a subset of authenticated participants
- private client-surface output
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
- assuming voice print alone is sufficient for all high-trust approvals in every context

## Follow-on work
Later specs should define:
- participant and principal domain models
- session audience-binding rules
- authentication-strength ladder for voice/web/device/telephony
- approval semantics for voice sessions
- wake-word to agent-target resolution
- room/device attachment model
- media-output strategy for low-latency home responses

## Related
- ADR 0001: context and goals
- ADR 0002: core harness plus profile packs
- ADR 0005: approval and policy model
- ADR 0006: v1 / v2 / v3 roadmap
- ADR 0010: inspiration from other repos
- ADR 0011: harness boundaries and client surfaces
