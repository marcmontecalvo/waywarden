# Orchestration Milestone Catalog

Catalogue of every `run.progress` `phase` / `milestone` pair used by the
orchestration service.  Every milestone value referenced by orchestration
code **must** appear here.

## Phases

### intake

| Milestone      | Description                                |
| -------------- | ------------------------------------------ |
| `received`     | Task received and parsed by the harness    |
| `accepted`     | Task accepted for processing               |

### plan

| Milestone            | Description                                |
| -------------------- | ------------------------------------------ |
| `drafted`            | Initial plan drafted                       |
| `approval_requested` | Plan submitted for approval gate           |
| `ready`              | Plan approved and ready for execution      |

### execute

| Milestone          | Description                           |
| ------------------ | ------------------------------------- |
| `tool_invoked`     | A tool invocation starts              |
| `artifact_emitted` | A tool or step produced an artifat    |
| `waiting_approval` | Execution paused at an approval gate  |

### review

| Milestone            | Description                       |
| -------------------- | --------------------------------- |
| `findings_recorded`  | Review findings are durably saved |

### handoff

| Milestone         | Description                              |
| ----------------- | ---------------------------------------- |
| `envelope_emitted` | Delegation envelope registered for child |

## Rules

- `phase` and `milestone` values are case-sensitive.
- Free-form strings are forbidden on `run.progress` events; callers
  **must** use values declared in this catalog.
- Adding a new milestone requires updating this catalog first.
