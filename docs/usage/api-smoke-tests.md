---
type: usage
title: "API Smoke Tests"
status: Active
date: 2026-04-27
tags: [usage, api, testing, smoke-tests]
---

# API Smoke Tests

These commands verify a running Waywarden instance. Run them against a local
server started with `make run` or `make dev`.

Base URL: `http://localhost:8000`

## Health check

```bash
curl -s http://localhost:8000/healthz | python3 -m json.tool
```

Expected:
```json
{
  "status": "ok",
  "app": "waywarden",
  "version": "0.1.0"
}
```

## Readiness check

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/readyz
```

Expected: `503` — this is correct behavior. `/readyz` is a fail-closed stub
until dependency health checks are wired in a later phase.

## List profiles (CLI)

```bash
uv run waywarden list-profiles
```

Expected output:
```
id        display_name          version
ea        Executive Assistant   1.0.0
coding    Coding                1.0.0
home      Home                  1.0.0
```

## List instances (CLI)

```bash
uv run waywarden list-instances
```

Expected output:
```
id        display_name  profile_id  config_path
marc-ea   Marc EA       ea          instances/marc-ea.yaml
```

## Submit a chat message

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Waywarden-Operator: smoke-test" \
  -d '{
    "session_id": "smoke-session-001",
    "message": "Hello, EA.",
    "policy_preset": "yolo"
  }' | python3 -m json.tool
```

Expected:
```json
{
  "run_id": "run-<hex>",
  "stream_url": "/api/runs/run-<hex>/events?last_seen_seq=0"
}
```

Status: `202 Accepted`

## Stream run events (SSE)

Replace `<run_id>` with the value from the previous response:

```bash
curl -N "http://localhost:8000/runs/<run_id>/events"
```

Expected: one or more SSE frames containing JSON-encoded run events:

```
data: {"id": "evt-run-...-created", "run_id": "run-...", "seq": 1, "type": "run.created", ...}
```

The stream closes when a terminal event (`run.completed`, `run.failed`, or
`run.cancelled`) is emitted, or you close the connection.

## Reconnect with last_seen_seq

To replay events from a specific sequence number:

```bash
curl -N "http://localhost:8000/runs/<run_id>/events?last_seen_seq=0"
```

If `last_seen_seq` exceeds the latest known sequence, the server returns `400`.

## Run visibility snapshot

```bash
curl -s http://localhost:8000/runs/<run_id>/view | python3 -m json.tool
```

Expected:
```json
{
  "run_state": "created",
  "milestones": [],
  "artifacts": [],
  "latest_checkpoint_ref": null,
  "manifest_summary": null
}
```

Returns `404` if the run ID is unknown.

## Missing operator header (should fail)

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "message": "test"}' | python3 -m json.tool
```

Expected: `401` with `{"detail": "missing X-Waywarden-Operator header"}`

## Memory read/write

Memory operations are not yet exposed as direct API endpoints. They occur
implicitly during run orchestration when `WAYWARDEN_MEMORY_PROVIDER=honcho` is
configured. Verify Honcho integration by checking run event payloads for
memory context injection when a run executes.

## Knowledge query

Knowledge queries are not yet exposed as direct API endpoints. They occur
implicitly during run orchestration. To verify filesystem knowledge, inspect
`assets/knowledge/` for available documents. To verify LLM-Wiki, check that
`LLM_WIKI_ENDPOINT` is reachable and returning results.

## Full local smoke test sequence

```bash
# 1. Health
curl -s http://localhost:8000/healthz | python3 -m json.tool

# 2. Submit a task
RUN_ID=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Waywarden-Operator: smoke-test" \
  -d '{"session_id": "smoke-001", "message": "Test task."}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])")
echo "Run ID: $RUN_ID"

# 3. Get snapshot
curl -s "http://localhost:8000/runs/$RUN_ID/view" | python3 -m json.tool

# 4. Stream events (press Ctrl+C to stop)
curl -N "http://localhost:8000/runs/$RUN_ID/events"
```
