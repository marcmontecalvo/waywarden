# ADR 0011: Harness boundaries and client surfaces

## Status
Accepted

## Problem
WayWarden is still pre-build, which makes it easy to accidentally fuse together:
- harness logic
- execution compute
- dashboard/UI concerns
- long-running state
- future integrations

Fast-moving market examples are converging on a clearer shape: durable harnesses, isolated compute, stable protocols, and multiple clients on top of the same runtime.

## Decision
WayWarden will be built as a **protocol-first harness** with clear separation between:
- control plane / orchestrator
- execution workers / sandboxes
- client surfaces

## Boundaries

### 1. Control plane
Owns:
- run orchestration
- task state
- approvals
- policy
- secrets and credential brokering
- durable checkpoints
- artifact registry
- session history

### 2. Execution workers
Own:
- task-local compute
- file operations inside the allowed workspace
- tool execution inside scoped boundaries
- disposable execution environments

Workers do **not** own:
- durable run state
- long-term policy
- top-level credentials by default

### 3. Client surfaces
Examples:
- dashboard
- CLI / operator console
- future desktop surface
- future HA-facing control surface
- future coding-runtime integration surface

Clients are views and interaction layers over the harness.
They are not the source of truth.

## Implications

### Protocol-first runtime
WayWarden should define stable internal contracts for:
- run creation
- events / streaming updates
- approvals
- artifact creation and retrieval
- checkpoint / resume
- handoff to external runtimes

### Durable server-side state
Runs must survive UI disconnects and worker loss.

### Manifest-driven execution
Each run should declare a shaped workspace and execution policy rather than relying on implicit repo mounts.

### Isolated sub-work
Subagents or delegated tasks should be able to run in isolated worker contexts with scoped tools and outputs.

### Layered memory
Keep separate:
- run-local scratch state
- user / relationship memory
- curated knowledge
- approvals / policy history
- task / session system of record

## Non-goals

- shipping desktop/computer-use support in v1
- making the dashboard the runtime center
- coupling the design to one provider SDK

## Follow-on work

- add workspace manifest model
- add run / event / checkpoint domain contracts
- define client-to-harness API surface
- define worker adapter boundary
- keep `research/` notes separate from canonical architecture
