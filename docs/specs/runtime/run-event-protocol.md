---
type: spec
title: "Run Event Protocol"
status: Ready for Build
date: 2026-04-18
spec_number: "RT-002"
phase: harness-core
relates_to_adrs: [0005, 0011]
depends_on: [0005-approval-model, 0011-harness-boundaries-and-client-surfaces, RT-001]
owner: core-runtime
target_milestone: "v1-harness"
revision: 2
---

# Run Event Protocol

Define the durable, append-only run event surface owned by the harness and shared across CLI, web, and future client surfaces.

## Scope

- Define run lifecycle events for creation, planning, execution, approval waits, resumptions, artifact creation, completion, failure, and cancellation
- Define the canonical event envelope and sequencing model
- Define reconnect semantics so clients can resume from durable server-side history after disconnect
- Define artifact and checkpoint reference formats exposed to clients
- Define how long-running and scheduled work resumes against existing durable run state

## Dependencies

- ADR `0011` for protocol-first harness and client/runtime separation
- ADR `0005` for approval and policy decisions
- `docs/specs/runtime/workspace-manifest.md`
- orchestration, artifact registry, checkpoint storage, and background scheduler services

## Intent

Clients must not infer run state from transient transport behavior, worker-local logs, or UI-local memory.
The harness owns the system of record and exposes it through a single append-only event history.

This follows the durable signals captured in:
- `docs/research/openai-codex-desktop-2026-04.md`: multiple client surfaces, reconnectable clients, durable server-side continuity, append-only history
- `docs/research/openai-agents-sdk-2026-04-15.md`: harness-owned durability, checkpoint and resume design, worker loss recovery, explicit separation between control plane and compute

The protocol is therefore a control-plane contract first and a transport concern second.

## Non-goals

- defining a websocket-only or SSE-only transport
- encoding provider SDK event types into the domain model
- making the CLI or future web UI the source of truth
- replacing durable run, checkpoint, or artifact records with ephemeral stream messages
- specifying worker-internal trace verbosity or tool-specific progress messages in v1

## Normative model

The run event protocol is an append-only ordered log attached to one run.
Every persisted event:
- belongs to exactly one `run_id`
- has a monotonically increasing `seq` within that run
- has a stable `id`
- has a typed `payload`
- may reference an originating event through `causation`

The harness is the only authority allowed to assign `seq`, persist events, and expose replay history.
Workers and channels may propose state changes, but they do not author the canonical event log directly.

## Run lifecycle

The normative top-level run phases in v1 are:
- `created`
- `planning`
- `executing`
- `waiting_approval`
- `completed`
- `failed`
- `cancelled`

These are run states, not event types.
Event types move the run between states or add durable references while the run remains in the same state.

## Event envelope

Every run event must conform to the following envelope.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | required | Stable event id unique across all run events |
| `run_id` | string | required | Stable run identifier |
| `seq` | integer | required | Monotonic per-run sequence number starting at `1` |
| `type` | enum | required | Event type from the catalog in this spec |
| `payload` | object | required | Type-specific structured payload |
| `timestamp` | RFC 3339 timestamp | required | Harness persistence time in UTC |
| `causation` | object or `null` | optional | Reference to the event or action that caused this event |
| `actor` | object or `null` | optional | Who or what caused the state transition |

### Envelope rules

- `id` should be a stable opaque identifier such as `evt_...`; clients must not derive ordering from it
- `seq` is the only normative ordering mechanism inside a run
- `seq` must increase by exactly `1` for each persisted event in a run
- `timestamp` is assigned by the harness when the event is durably recorded, not when a worker first emitted an intent
- `payload` must be JSON-serializable and provider-neutral
- unknown top-level envelope fields must be ignored by clients for forward compatibility
- event deletion and in-place mutation are forbidden

## Causation model

`causation` is used to explain why an event exists without requiring clients to infer history from prose.

Shape:
- `event_id`: optional string id of the immediately preceding causal event
- `action`: optional string such as `operator_resume`, `approval_granted`, `scheduler_wakeup`, `worker_report`
- `request_id`: optional string for the inbound API or command invocation that triggered the change

Rules:
- at least one of `event_id`, `action`, or `request_id` must be present when `causation` is not null
- `event_id`, when present, must reference an earlier event in the same run
- causation is explanatory metadata and must not be used as an alternate ordering mechanism

## Actor model

`actor` identifies the origin of a transition in provider-neutral terms.

Shape:
- `kind`: enum: `operator`, `system`, `scheduler`, `worker`, `policy-engine`
- `id`: optional stable logical id such as `user:marc`, `worker:lease_123`, `scheduler:default`
- `display`: optional short human-readable label

Rules:
- actor ids must remain logical harness ids, not provider credential ids
- clients may display `display` when present but must not rely on it for identity

## Event catalog

The following event types are required for v1.

| Event Type | Purpose | Run State After Event | Required Payload Fields | Optional Payload Fields |
| --- | --- | --- | --- | --- |
| `run.created` | Durable run record created and accepted by the harness | `created` | `instance_id`, `profile`, `policy_preset`, `manifest_ref`, `entrypoint` | `initial_objective`, `task_ref` |
| `run.plan_ready` | Initial plan or revised plan durably accepted for execution | `planning` | `plan_ref`, `summary`, `revision`, `approval_required` | `checkpoint_ref`, `supersedes_plan_ref` |
| `run.execution_started` | Execution phase has started or restarted | `executing` | `worker_session_ref`, `attempt`, `resume_kind` | `checkpoint_ref`, `lease_expires_at` |
| `run.progress` | Operator-visible milestone within the current run state; does not change run state | unchanged | `phase`, `milestone` | `detail`, `checkpoint_ref`, `source_event_id` |
| `run.approval_waiting` | Run is blocked on an approval decision | `waiting_approval` | `approval_id`, `approval_kind`, `summary` | `expires_at`, `checkpoint_ref`, `requested_capability` |
| `run.resumed` | Run resumed after approval, disconnect recovery, scheduler wake-up, or worker restart | `executing` | `resume_kind`, `resumed_from_seq` | `checkpoint_ref`, `worker_session_ref`, `approval_id` |
| `run.artifact_created` | Durable artifact was registered for operator or downstream use | unchanged | `artifact_ref`, `artifact_kind`, `label` | `source_event_id`, `checkpoint_ref`, `content_type` |
| `run.completed` | Run finished successfully | `completed` | `outcome` | `final_checkpoint_ref`, `artifact_refs`, `summary_ref` |
| `run.failed` | Run finished unsuccessfully and will not continue without explicit new action | `failed` | `failure_code`, `message`, `retryable` | `final_checkpoint_ref`, `artifact_refs`, `failed_event_id` |
| `run.cancelled` | Run was explicitly cancelled by operator or policy | `cancelled` | `reason` | `final_checkpoint_ref`, `cancelled_by` |

`unchanged` means the event does not itself change the top-level run state.
For example, `run.artifact_created` may occur during `planning`, `executing`, or `waiting_approval`.

## Event payload definitions

### `run.created`

Purpose:
Persist the creation of the run and the immutable execution inputs known at submission time.

Required payload fields:
- `instance_id`: string
- `profile`: string
- `policy_preset`: enum: `yolo`, `ask`, `allowlist`, `custom`
- `manifest_ref`: string workspace manifest reference
- `entrypoint`: enum: `api`, `cli`, `scheduler`, `internal`

Optional payload fields:
- `initial_objective`: string
- `task_ref`: string

Rules:
- `manifest_ref` must point to the effective manifest version attached to the run
- `policy_preset` must align with ADR `0005`

### `run.plan_ready`

Purpose:
Record that the harness accepted a durable plan suitable for rendering or approval.

Required payload fields:
- `plan_ref`: string
- `summary`: string
- `revision`: integer
- `approval_required`: boolean

Optional payload fields:
- `checkpoint_ref`: string
- `supersedes_plan_ref`: string

Rules:
- every new accepted plan revision emits a new `run.plan_ready`
- `summary` must be short enough for client surfaces to render as a headline, not the full plan body
- detailed plan content lives behind `plan_ref`, not inline

### `run.execution_started`

Purpose:
Mark the start of active execution work in a worker or equivalent runtime.

Required payload fields:
- `worker_session_ref`: string
- `attempt`: integer
- `resume_kind`: enum: `fresh_start`, `post_approval`, `post_disconnect`, `post_worker_loss`, `scheduled_wakeup`

Optional payload fields:
- `checkpoint_ref`: string
- `lease_expires_at`: RFC 3339 timestamp

Rules:
- the first execution attempt must set `attempt` to `1`
- `checkpoint_ref` is required when `resume_kind` is not `fresh_start`

### `run.progress`

Purpose:
Record an operator-visible milestone inside the current run state without changing that state.
Used by the orchestration service to surface sub-phase progress (for example, `intake.received`, `plan.drafted`, `execute.tool_invoked`, `review.findings`, `handoff.envelope_emitted`) while the run remains in `planning` or `executing`.

Required payload fields:
- `phase`: string stable identifier for the orchestration sub-phase (for example `intake`, `plan`, `execute`, `review`, `handoff`)
- `milestone`: string stable identifier for the specific milestone within that phase

Optional payload fields:
- `detail`: string or typed object with non-sensitive operator-facing context
- `checkpoint_ref`: string
- `source_event_id`: string referencing the event that produced this milestone (for example an earlier `run.artifact_created`)

Rules:
- `run.progress` must never change the run's top-level state; the state column for this event type is always `unchanged`
- `phase` and `milestone` values must be declared in the orchestration service's documented milestone catalog — free-form strings are invalid
- `detail` must be redaction-safe for operator surfaces; raw tool output or secrets must be written through `run.artifact_created` instead
- terminal events suppress further `run.progress`; no `run.progress` may follow `run.completed`, `run.failed`, or `run.cancelled`

### `run.approval_waiting`

Purpose:
Record that execution is durably paused pending an explicit decision.

Required payload fields:
- `approval_id`: string
- `approval_kind`: string
- `summary`: string

Optional payload fields:
- `expires_at`: RFC 3339 timestamp
- `checkpoint_ref`: string
- `requested_capability`: string

Rules:
- this event must be emitted only after the approval record is persisted
- if resumable context exists, `checkpoint_ref` should be included so the subsequent resume can bind to the same paused work

### `run.resumed`

Purpose:
Record the transition back into active work after a durable pause or recovery event.

Required payload fields:
- `resume_kind`: enum: `approval_granted`, `operator_resume`, `scheduler_wakeup`, `worker_recovery`, `transport_rebind`
- `resumed_from_seq`: integer

Optional payload fields:
- `checkpoint_ref`: string
- `worker_session_ref`: string
- `approval_id`: string

Rules:
- `resumed_from_seq` must be the latest persisted sequence that the resumed execution context is known to include
- `transport_rebind` is used when a client reconnects and the run continues in the same durable execution context; it records continuity without implying a new plan revision

### `run.artifact_created`

Purpose:
Expose a stable artifact registration while the run is still active or after completion.

Required payload fields:
- `artifact_ref`: string
- `artifact_kind`: string
- `label`: string

Optional payload fields:
- `source_event_id`: string
- `checkpoint_ref`: string
- `content_type`: string

Rules:
- the event must be emitted only after the artifact registry accepts `artifact_ref`
- clients should treat the event as a durable pointer, not the artifact payload itself

### `run.completed`

Purpose:
Mark a successful terminal state.

Required payload fields:
- `outcome`: string

Optional payload fields:
- `final_checkpoint_ref`: string
- `artifact_refs`: list of strings
- `summary_ref`: string

Rules:
- terminal events are mutually exclusive; once `run.completed` exists, no later non-terminal event may be appended
- `artifact_refs` should list the primary operator-visible artifacts, not every transient file

### `run.failed`

Purpose:
Mark an unsuccessful terminal state.

Required payload fields:
- `failure_code`: string
- `message`: string
- `retryable`: boolean

Optional payload fields:
- `final_checkpoint_ref`: string
- `artifact_refs`: list of strings
- `failed_event_id`: string

Rules:
- `message` should be operator-readable and concise
- `retryable` indicates whether a future explicit action may create a new attempt, not whether the failed run remains active

### `run.cancelled`

Purpose:
Mark an explicit cancellation terminal state.

Required payload fields:
- `reason`: string

Optional payload fields:
- `final_checkpoint_ref`: string
- `cancelled_by`: string

Rules:
- cancellations must remain distinguishable from failures for audit and operator reporting

## Approval decision event mapping

`run.approval_waiting` records entry into the `waiting_approval` state. Resolution of that wait is mapped to existing events as follows, with no new event type required:

- approval granted: emit `run.resumed` with `resume_kind = approval_granted`; run state transitions to `executing`. `approval_id` must be present in the payload.
- approval denied and run is abandoned: emit `run.cancelled` with `reason = approval_denied` and `cancelled_by` set to the operator or policy that denied. Run state transitions to `cancelled`.
- approval denied and the harness chooses to continue along an alternate path without the gated action: emit `run.resumed` with `resume_kind = approval_denied_alternate_path` and `approval_id` set; the continuation must not perform the denied action.
- approval timeout: emit either `run.cancelled` with `reason = approval_timeout` or `run.failed` with `failure_code = approval_timeout`, depending on whether retry is possible; `retryable` on `run.failed` indicates whether a new attempt may be initiated.

The harness must not invent `approval_requested` or `approval_decided` event types; the approval record referenced by `approval_id` is the persisted decision artifact, and its decisions are reflected through the events above.

## Token usage accounting

Token usage records (prompt tokens, completion tokens, model, provider) are persisted outside the RT-002 event log.

- per-call usage entries are written through a dedicated `TokenUsageRepository` keyed on `run_id` and an internal sequence, not through `RunEventRepository`.
- a run-scoped usage summary may be registered as a durable artifact via `run.artifact_created` with `artifact_kind = usage-summary` once a run reaches a terminal state.
- implementations must not append `run.usage` or similar non-catalog event types; catalog violations are a replay hazard for clients.

## Artifact and checkpoint references

Clients need stable references, not storage-specific implementation details.

### Artifact reference format

Normative shape:
`artifact://runs/{run_id}/{artifact_id}`

Examples:
- `artifact://runs/run_123/art_001`
- `artifact://runs/run_123/art_final_report`

Rules:
- `artifact_id` must be unique within a run
- artifact refs are opaque identifiers for clients; clients must not infer storage paths from them
- artifact metadata such as filename, size, and content type is retrieved through artifact APIs, not encoded into the ref

### Checkpoint reference format

Normative shape:
`checkpoint://runs/{run_id}/{checkpoint_id}`

Examples:
- `checkpoint://runs/run_123/chk_plan_v1`
- `checkpoint://runs/run_123/chk_pre_approval_002`

Rules:
- checkpoints represent durable resumable state owned by the harness
- checkpoints may point to run state snapshots, worker recovery state, or both, but that storage detail is not part of the ref
- clients may surface checkpoint refs for operator diagnostics, but resume operations should use API-level commands rather than reconstructing state from the ref string

## Sequencing and replay

### Sequencing rules

- sequence numbering is per run, not global
- `seq = 1` must always be `run.created`
- gaps in `seq` are invalid
- replay order is ascending `seq`
- if two actions happen concurrently, the harness serializes them into one authoritative append order before making them visible

### Replay contract

The harness must support replay of events for one run in ascending `seq` order.
Replay is the source of truth for:
- reconnecting client surfaces
- rebuilding operator-visible progress
- hydrating approval waits and artifact links
- recovering state after transport interruption

Clients must be able to render a complete operator view using:
- the current run record
- the ordered event history
- API lookups for referenced artifacts, approvals, checkpoints, and plans

## Reconnect semantics

Clients reconnect using `last_seen_seq`.

Normative behavior:
- if the client has never seen any event for the run, it requests from `last_seen_seq = 0`
- the harness returns all events where `seq > last_seen_seq`
- if no new events exist, the harness may return an empty page or hold the transport open depending on protocol choice
- if `last_seen_seq` is greater than the current max `seq`, the harness must reject the request as invalid
- if the requested run no longer exists or is not visible to the client, normal authorization and not-found behavior applies

### Durable reconnect rules

- reconnect never changes run state by itself
- reconnect must not require clients to rebuild state from worker-local transcripts
- the server remains authoritative even if the worker or client restarts
- clients must tolerate duplicate delivery at the transport layer by de-duplicating on `id` or `seq`

### Example reconnect flow

1. CLI receives events through `seq = 18` and disconnects.
2. While disconnected, the harness persists `run.artifact_created` at `seq = 19` and `run.approval_waiting` at `seq = 20`.
3. CLI reconnects with `last_seen_seq = 18`.
4. Harness returns events `19` and `20`.
5. CLI renders the new artifact and approval wait without asking the worker what happened.

## Long-running and scheduled resume semantics

Long-running work must resume against durable harness state, not ad hoc in-memory scheduler state.

### Normative rules

- a scheduler wake-up must bind to an existing run record
- resumption must use the latest accepted run state plus any referenced checkpoint
- a resume path must emit `run.resumed` before additional active execution events are emitted
- if a new worker session is created, `run.execution_started` must follow `run.resumed`
- if the run is already terminal, scheduled wake-up must do nothing and must not append new lifecycle events

### Durable resume kinds

The harness must distinguish at least:
- `approval_granted`: execution can continue because an approval wait resolved positively
- `operator_resume`: an operator explicitly asked the harness to continue a paused run
- `scheduler_wakeup`: a scheduled job resumed a run at a future time
- `worker_recovery`: the control plane resumed after worker loss or lease expiry
- `transport_rebind`: a client reattached to active durable run state

### Resume safety rules

- the harness must not resume from a checkpoint tied to a different run
- the harness must not resume against a changed manifest without creating a new durable run revision
- approvals resolved while a client is offline must still be visible as durable state through replay
- worker loss must not erase artifact refs, approval history, or accepted plans

## Client surface obligations

Client surfaces may:
- render run state from replayed events
- request missing artifacts, checkpoints, approvals, or plan bodies through APIs
- keep local cursors such as `last_seen_seq`

Client surfaces may not:
- invent canonical sequence numbers
- mutate or delete event history
- treat transport connection state as equivalent to run state
- store the only copy of artifacts, approvals, or resumable progress

## Build implications

Implementation of RT-002 should produce:
- typed domain models for run events, event causation, actor identity, and reference objects
- durable per-run sequence assignment in the control plane
- replay APIs that support `last_seen_seq` reconnect behavior
- artifact and checkpoint registries that emit durable refs before related events become visible
- scheduler and approval flows that resume against run state rather than worker-local memory
- terminal-state guards so no non-terminal events are appended after completion, failure, or cancellation

This spec is ready for build once those contracts exist in code and the run orchestration service uses them as the only operator-visible source of truth.
