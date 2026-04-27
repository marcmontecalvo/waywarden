---
type: usage
title: "EA Operator Guide"
status: Active
date: 2026-04-27
tags: [usage, ea, operator, tasks, approvals]
---

# EA Operator Guide

This guide describes what the Executive Assistant (EA) profile can do today,
how tasks flow through the system, and how to interact with a running instance.

## What EA can do today (P5/P6 state)

**Task management**
- Accept task requests via `POST /chat`
- Create tasks in `draft` state with session, title, and objective
- Advance tasks through the state machine: draft → planning → executing →
  waiting_approval → completed / failed / cancelled
- Persist all task state to PostgreSQL

**Run lifecycle and event streaming**
- Create runs with durable RT-002 event logs
- Emit canonical events: `run.created`, `run.progress`, `run.artifact_created`,
  `run.completed`, `run.failed`, `run.cancelled`
- Stream events to clients via SSE (`GET /runs/{run_id}/events`)
- Provide run snapshots on demand (`GET /runs/{run_id}/view`)

**Approval workflow**
- Request approval checkpoints (task transitions to `waiting_approval`)
- Support approval kinds: `ea_checkpoint`
- Accept approval decisions:
  - Granted → task resumes planning/executing
  - Denied (abandon) → task transitions to cancelled
  - Denied (alternate path) → task returns to planning
  - Timeout → task transitions to failed

**Orchestration routines** (wired, background dispatch pending)
- `EABriefingHandler` — generates dated briefing from inbox state and tasks
- `EAIboxTriageHandler` — classifies inbox items, drafts responses, routes to approval
- `EASchedulerHandler` — picks tasks from queue, schedules, dispatches with approval gates

**Memory** (optional, requires Honcho)
- Inject conversation memory into EA context
- Defaults to fake in-process memory when Honcho is not configured

**Knowledge** (optional, requires LLM-Wiki or filesystem assets)
- Inject relevant SOPs and project context into EA context
- Defaults to filesystem knowledge at `assets/knowledge/` when LLM-Wiki is not configured

**Token accounting**
- Measures user-input tokens, injected context, tool expansion, and response tokens per turn

## What EA cannot do yet

- **Live background orchestration**: `POST /chat` creates a run and emits
  `run.created`, but does not yet dispatch the orchestration pipeline in the
  background. The orchestration dispatch TODO is tracked for a later phase.
- **Session conversation memory persistence**: the Message domain model exists,
  but messages are not yet persisted across sessions.
- **Readiness checks**: `GET /readyz` always returns 503; dependency health
  checks are not yet wired.
- **Web channel**: the webhook channel adapter is stubbed; external webhook
  delivery is not yet wired.
- **Multi-instance routing**: instance selection in the API is a stub; all
  requests are routed to `instance-stub` today.

## Task flow

```
Client                    Waywarden API              Database
  |                           |                          |
  |-- POST /chat -----------> |                          |
  |   (session_id, message)   |                          |
  |                           |-- create Task (draft) -> |
  |                           |-- create Run (created) ->|
  |                           |-- emit run.created ------>|
  |<-- 202 ChatResponse ------|                          |
  |   (run_id, stream_url)    |                          |
  |                           |                          |
  |-- GET /runs/{id}/events ->|                          |
  |   (SSE stream)            |<-- read events ----------|
  |<-- SSE: run.created ------|                          |
  |<-- SSE: ... progress ... -|                          |
  |<-- SSE: run.completed ----|                          |
```

## Memory flow

When `WAYWARDEN_MEMORY_PROVIDER=honcho`:

1. At run start, the harness queries Honcho for recent memory for the session.
2. Relevant memories are injected into the EA context under the token cap
   (`WAYWARDEN_CONTEXT_MEMORY_CHAR_CAP`, default 2000 chars).
3. After a run completes, new memories may be written back to Honcho.

With the `fake` provider, memory is ephemeral and scoped to the process.

## Knowledge lookup flow

When `WAYWARDEN_KNOWLEDGE_PROVIDER=llm_wiki`:

1. At run start, the harness queries LLM-Wiki with the task objective as the
   query.
2. Relevant documents are injected into EA context under the token cap
   (`WAYWARDEN_CONTEXT_KNOWLEDGE_CHAR_CAP`, default 2000 chars).
3. Knowledge is read-only from the harness side.

With `filesystem` provider, the harness reads from `assets/knowledge/`.

## Approvals flow

1. During task execution, the EA orchestrator requests an approval checkpoint.
2. The task transitions to `waiting_approval`; a `run.approval_requested` event
   is emitted.
3. An operator (or automated policy) submits a decision.
4. The task resumes or is cancelled based on the decision.
5. Policy preset controls the default behavior:
   - `yolo` — all checkpoints auto-approve
   - `ask` — checkpoint waits for operator response (default)
   - `allowlist` — only allow-listed actions are auto-approved

## Delegation envelope behavior

When an EA task is handed off to a sub-agent (e.g., the coding agent), a
`DelegationEnvelope` is constructed containing:
- the task objective
- the authorized scope
- the originating session and run IDs
- the policy preset inherited from the parent run

The sub-agent receives the envelope and operates within its declared boundaries.
Delegation is tracked in the event log as `run.delegated`.

## Example API calls

### Submit a task

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Waywarden-Operator: operator-local" \
  -d '{
    "session_id": "session-abc123",
    "message": "Draft a weekly status report for the waywarden project.",
    "policy_preset": "ask"
  }' | python3 -m json.tool
```

Response:

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "stream_url": "/api/runs/run-a1b2c3d4e5f6/events?last_seen_seq=0"
}
```

### Stream run events

```bash
curl -N http://localhost:8000/runs/run-a1b2c3d4e5f6/events
```

Each SSE frame contains a JSON-encoded `RunEvent`.

### Get a run snapshot

```bash
curl -s http://localhost:8000/runs/run-a1b2c3d4e5f6/view | python3 -m json.tool
```

### List profiles (CLI)

```bash
uv run waywarden list-profiles
```

### List instances (CLI)

```bash
uv run waywarden list-instances
```

### Submit a chat message (CLI)

```bash
uv run waywarden chat --session session-abc123 "Summarize today's tasks."
```
