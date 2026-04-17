---
type: spec
title: "Workspace Manifest Model"
status: Ready for Build
date: 2026-04-17
spec_number: "RT-001"
phase: harness-core
relates_to_adrs: [0005, 0011]
depends_on: [0005-approval-model, 0011-harness-boundaries-and-client-surfaces]
owner: core-runtime
target_milestone: "v1-harness"
---

# Workspace Manifest Model

Define the shaped execution workspace declared by the harness before any worker or delegated task starts.

## Scope

- Define manifest fields for `inputs`, `writable_paths`, `outputs`, `network_policy`, `tool_policy`, `secret_scope`, and `snapshot_policy`
- Define which manifest fields are harness-owned versus worker-consumed
- Define validation rules so manifests stay provider-neutral and profile-aware
- Define how manifests are attached to runs, delegated tasks, and isolated sub-work

## Dependencies

- ADR `0005` for policy presets and approval classes
- ADR `0011` for control-plane, worker, and client-surface boundaries
- Domain models for runs, checkpoints, and artifacts

## Intent

Waywarden workers must not infer their filesystem, tool, network, or secret access from an implicit mounted environment.
The harness declares that shape explicitly and durably before work starts.

This follows the same durable architecture signals captured in `docs/research/openai-agents-sdk-2026-04-15.md`:
- explicit manifest-shaped workspaces
- harness-owned control over secrets and policy
- isolated sub-work instead of one shared mutable sandbox
- durable recovery after worker loss

The manifest is therefore a control-plane contract first and a worker input second.

## Non-goals

- standardizing a provider SDK payload
- describing UI behavior
- embedding provider-specific sandbox or MCP types into the domain model
- replacing run events, checkpoints, or artifact records

## Normative model

The workspace manifest is a typed object attached to a run or delegated work item.
In v1, the normative fields are:
- `inputs`
- `writable_paths`
- `outputs`
- `network_policy`
- `tool_policy`
- `secret_scope`
- `snapshot_policy`

The harness may store extra internal metadata alongside the manifest record, but that metadata is not part of the worker-consumed contract unless it is promoted into this spec.

## Field matrix

| Field | Type | Owner | Required | Example |
| --- | --- | --- | --- | --- |
| `inputs` | list of input mounts | harness | required | `[{ "name": "repo", "kind": "directory", "source_ref": "artifact://workspace/repo", "target_path": "/workspace/repo", "read_only": true }]` |
| `writable_paths` | list of writable path grants | harness | required | `[{ "path": "/workspace/run", "purpose": "task-scratch" }, { "path": "/workspace/output", "purpose": "declared-output" }]` |
| `outputs` | list of declared output contracts | harness | required | `[{ "name": "patches", "path": "/workspace/output/patches", "kind": "directory", "required": false }]` |
| `network_policy` | network policy object | harness | required | `{ "mode": "deny", "allow": [] }` |
| `tool_policy` | tool policy object | harness | required | `{ "preset": "ask", "rules": [{ "tool": "shell", "action": "write", "decision": "approval-required" }] }` |
| `secret_scope` | secret exposure object | harness | required | `{ "mode": "brokered", "allowed_secret_refs": ["calendar.default"], "mount_env": [] }` |
| `snapshot_policy` | checkpoint and retention object | harness | required | `{ "on_start": false, "on_completion": true, "on_failure": true, "before_destructive_actions": true }` |

Worker ownership is intentionally omitted from the field table because workers do not author the manifest.
Workers consume the validated contract and may emit violations or capability mismatches, but they do not broaden it.

## Field definitions

### `inputs`

Purpose:
Describe the read-only or explicitly mutable materialized inputs the harness provides to the worker.

Type:
A non-empty list of input mount objects.

Input mount shape:
- `name`: string identifier unique within the manifest
- `kind`: enum: `file`, `directory`, `artifact`, `bundle`, `memory-export`, `knowledge-export`
- `source_ref`: provider-neutral string reference owned by the harness
- `target_path`: absolute in-sandbox path
- `read_only`: boolean
- `required`: boolean, default `true`
- `description`: optional string

Rules:
- `target_path` must be absolute and normalized
- two inputs must not resolve to the same `target_path`
- `source_ref` must be harness-resolvable without exposing provider-specific types in the domain layer
- `memory-export` and `knowledge-export` remain separate `kind` values to preserve the memory/knowledge boundary
- mutable inputs are allowed only when the harness can explain why they are not better modeled as `writable_paths`

### `writable_paths`

Purpose:
Declare the only in-workspace paths the worker may write to.

Type:
A list of writable path grant objects.

Writable path grant shape:
- `path`: absolute in-sandbox path
- `purpose`: string such as `task-scratch`, `declared-output`, `cache`, or `checkout-copy`
- `max_size_mb`: optional integer
- `retention`: optional enum: `ephemeral`, `run-retained`, `artifact-promoted`

Rules:
- every writable path must be absolute and normalized
- writable paths must not overlap implicitly; if one path contains another, both must be rejected unless the harness marks the narrower path as redundant and drops it during normalization
- a worker must be denied writes outside declared writable paths even if the underlying runtime could technically allow them
- profile overlays may narrow writable paths but must not silently widen them

### `outputs`

Purpose:
Describe which artifacts the harness expects or accepts from the run.

Type:
A list of declared output contracts.

Output contract shape:
- `name`: string identifier unique within the manifest
- `path`: absolute in-sandbox path
- `kind`: enum: `file`, `directory`, `json`, `log`, `patch-set`, `report`
- `required`: boolean
- `promote_to_artifact`: boolean, default `true`
- `description`: optional string

Rules:
- every output `path` must be inside a declared `writable_paths` grant
- outputs are declarations, not proof of completion; actual existence is checked at collection time
- an output may be optional, but required outputs must trigger run failure or degraded completion status if missing

### `network_policy`

Purpose:
State whether the worker may use the network and, if so, within what scope.

Type:
A network policy object.

Shape:
- `mode`: enum: `deny`, `allowlist`, `profile-default`
- `allow`: list of allow rules, default empty
- `deny`: optional list of deny rules for audit clarity

Allow rule shape:
- `host_pattern`: string
- `port`: optional integer
- `scheme`: optional enum: `https`, `http`, `ssh`, `tcp`
- `purpose`: required string

Rules:
- `deny` mode means no outbound network access
- `profile-default` must resolve to a concrete normalized policy before the worker starts
- `allowlist` rules must be explicit enough for audit and replay; free-form prose is invalid
- the manifest must not rely on a provider-specific firewall object

### `tool_policy`

Purpose:
Attach the resolved tool-execution policy that applies inside the declared workspace.

Type:
A tool policy object.

Shape:
- `preset`: enum: `yolo`, `ask`, `allowlist`, `custom`
- `rules`: list of tool decision rules
- `default_decision`: enum: `auto-allow`, `approval-required`, `forbidden`

Tool decision rule shape:
- `tool`: provider-neutral tool capability id such as `shell`, `http`, `calendar-read`, `calendar-write`
- `action`: optional narrower action string such as `read`, `write`, `delete`, `exec`
- `decision`: enum: `auto-allow`, `approval-required`, `forbidden`
- `reason`: optional string for traceability

Rules:
- `preset` must map cleanly to ADR `0005`
- the manifest stores resolved behavior, not just a preset name
- tool ids must be capability-oriented and provider-neutral
- channel adapters must not override or bypass `tool_policy`

### `secret_scope`

Purpose:
Describe which secrets the worker may access and by what mechanism.

Type:
A secret exposure object.

Shape:
- `mode`: enum: `none`, `brokered`, `env-mounted`
- `allowed_secret_refs`: list of harness-owned secret references
- `mount_env`: list of environment variable names that may be materialized, default empty
- `redaction_level`: enum: `full`, `names-only`, `none`

Rules:
- secret references must be harness-managed logical ids, not raw provider credential payloads
- `brokered` is preferred; `env-mounted` is allowed only when a tool or worker adapter requires process-local secret material
- a worker must not learn secrets outside `allowed_secret_refs`
- secrets granted to a delegated task should default to a narrower set than the parent run

### `snapshot_policy`

Purpose:
Control durable capture of workspace state and artifact-oriented checkpoints.

Type:
A snapshot and checkpoint object.

Shape:
- `on_start`: boolean
- `on_completion`: boolean
- `on_failure`: boolean
- `before_destructive_actions`: boolean
- `max_snapshots`: optional integer
- `include_paths`: optional list of absolute paths
- `exclude_paths`: optional list of absolute paths

Rules:
- snapshot settings govern harness capture behavior, not worker discretion
- include and exclude paths must resolve only within declared inputs or writable paths
- secret-bearing paths must be excluded or redacted according to `secret_scope`
- `before_destructive_actions` applies to actions classified as destructive by resolved `tool_policy`

## Ownership model

### Harness-owned

The harness is the only authority that may:
- create the manifest
- normalize profile defaults into concrete policy
- attach secret references
- resolve preset-driven tool rules into explicit decisions
- decide snapshot capture policy
- persist the manifest with the run record

### Worker-consumed

The worker may:
- read the manifest
- reject the run if it cannot honor the declared constraints
- emit violations when the runtime environment differs from the manifest
- write only within declared writable paths
- produce outputs only within declared output locations

The worker may not:
- widen tools, secrets, network, or writable paths
- rewrite the manifest in place
- reinterpret profile defaults at runtime

## Validation rules

Validation occurs in two phases.

### 1. Schema validation

The manifest must satisfy:
- all seven normative fields are present
- enum values are recognized
- all declared paths are absolute, normalized, and unique where uniqueness is required
- all references are typed as provider-neutral strings or typed domain enums
- all outputs live inside writable paths

### 2. Policy and profile validation

The manifest must also satisfy:
- the selected profile is allowed to request the declared tool capabilities
- the selected policy preset can produce the declared `tool_policy`
- secret references are allowed for the instance and profile
- network permissions do not exceed the profile or operator policy envelope
- writable paths do not escape the instance workspace root
- attachment semantics are valid for the work type being started

Validation must happen in the control plane before a worker lease is created.
Workers may perform a second capability check, but that is defensive verification, not the primary approval point.

## Attachment semantics

### Run attachment

Every run gets exactly one effective workspace manifest.
That manifest is immutable after the run starts except through a new run revision emitted by the harness.
The effective manifest is stored with the durable run record so the system can recover after worker loss.

### Delegated task attachment

A delegated task gets its own manifest derived from the parent run.
The child manifest must be a narrowing transform of the parent on:
- `writable_paths`
- `network_policy`
- `tool_policy`
- `secret_scope`

The child may receive a reduced input set or copied inputs, but it may not inherit broader authority than the parent.

### Isolated sub-work attachment

Isolated sub-work, including future subagents or sandboxed helper jobs, must default to a separate manifest even when launched from the same top-level run.
It may share logical input references with the parent, but it should not share one giant mutable workspace by default.
Outputs from isolated sub-work are promoted back into the parent run only through declared output collection and artifact registration.

### Resume attachment

When a run resumes after interruption or worker loss, the harness reattaches the same effective manifest version unless an explicit run revision is created.
Resuming against a changed manifest without revisioning is invalid because it breaks replayability and auditability.

## Normalization rules

Before persistence and worker dispatch, the harness should normalize:
- `profile-default` network settings into concrete `deny` or `allowlist` mode
- policy presets into explicit `tool_policy.rules`
- relative operator intent into absolute in-sandbox paths
- duplicate or overlapping declarations into a rejected manifest rather than ambiguous worker behavior

Normalization is a harness responsibility because workers should consume a concrete contract, not a partially interpreted profile overlay.

## Example

```json
{
  "inputs": [
    {
      "name": "repo",
      "kind": "directory",
      "source_ref": "artifact://workspace/repo",
      "target_path": "/workspace/repo",
      "read_only": true,
      "required": true,
      "description": "Operator-provided repository checkout"
    },
    {
      "name": "task-brief",
      "kind": "file",
      "source_ref": "artifact://runs/run_123/brief.md",
      "target_path": "/workspace/context/brief.md",
      "read_only": true,
      "required": true
    }
  ],
  "writable_paths": [
    {
      "path": "/workspace/run",
      "purpose": "task-scratch",
      "retention": "ephemeral"
    },
    {
      "path": "/workspace/output",
      "purpose": "declared-output",
      "retention": "artifact-promoted"
    }
  ],
  "outputs": [
    {
      "name": "final-report",
      "path": "/workspace/output/report.json",
      "kind": "json",
      "required": true,
      "promote_to_artifact": true
    }
  ],
  "network_policy": {
    "mode": "allowlist",
    "allow": [
      {
        "host_pattern": "api.github.com",
        "scheme": "https",
        "purpose": "issue-and-pr-metadata"
      }
    ],
    "deny": []
  },
  "tool_policy": {
    "preset": "ask",
    "default_decision": "approval-required",
    "rules": [
      {
        "tool": "shell",
        "action": "read",
        "decision": "auto-allow"
      },
      {
        "tool": "shell",
        "action": "write",
        "decision": "approval-required"
      }
    ]
  },
  "secret_scope": {
    "mode": "brokered",
    "allowed_secret_refs": ["github.default"],
    "mount_env": [],
    "redaction_level": "full"
  },
  "snapshot_policy": {
    "on_start": false,
    "on_completion": true,
    "on_failure": true,
    "before_destructive_actions": true,
    "max_snapshots": 3,
    "include_paths": [
      "/workspace/output"
    ],
    "exclude_paths": [
      "/workspace/run/tmp"
    ]
  }
}
```

## Build implications

Implementation of RT-001 should produce:
- a typed domain model for the manifest and its nested policy objects
- control-plane validation before worker dispatch
- worker adapter verification that the concrete runtime matches the manifest
- durable storage of the effective manifest version with the run record
- narrowing logic for delegated tasks and isolated sub-work

This spec is ready for build once those contracts are implemented in code and referenced by RT-002 and later worker-boundary work.
