---
type: research
title: "OpenAI Agents SDK — Harness & Manifest Design"
status: Captured
date: 2026-04-17
source_url: "https://openai.com/index/the-next-evolution-of-the-agents-sdk/"
source_type: product
priority: directly-relevant
tags: [harness, sdk, manifest, durability, isolation]
relates_to_adrs: [0001, 0011]
---

# OpenAI Agents SDK update (2026-04-15)

## What is actually strong here?

The strongest part is not the branding.
It is the explicit elevation of the **harness** into a first-class system with:
- configurable memory
- sandbox-aware orchestration
- filesystem and shell execution primitives
- `apply_patch` style file edits
- MCP support
- AGENTS.md support
- skills / progressive disclosure
- native sandbox execution
- workspace manifests
- externalized state for durability
- isolated subagent sandboxes

## Why it matters for WayWarden

This aligns with where WayWarden should go, but it also sharpens a few requirements:

- the harness is a real subsystem, not glue code
- harness and compute should be separate
- the agent workspace should be declared explicitly
- run state should survive sandbox loss
- subagents should not share one giant mutable workspace by default
- instruction/tool loading should be selective to reduce token bloat

## What we should borrow

### 1. Harness vs compute separation
Treat the control plane and execution plane as separate from day one.

Borrow:
- orchestration outside the sandbox
- secrets staying out of model-generated compute where possible
- disposable sandboxes
- checkpoint / resume design

### 2. Manifest-shaped workspaces
WayWarden should define workspaces explicitly rather than implicitly through a mounted repo.

Useful manifest fields:
- inputs
- writable paths
- outputs
- network policy
- tool policy
- secret scope
- snapshot policy

### 3. Progressive disclosure
Do not preload every prompt, tool description, or skill.

Borrow:
- skill catalogs
- just-in-time instruction loading
- context narrowing by role and task

### 4. Isolated subagent execution
Subagents should be able to run in separate sandboxes with scoped tools and outputs.

### 5. Durable execution
Externalize run state, tool outputs, and checkpoints so the system can recover from worker loss.

## What we should avoid

- treating the SDK itself as the product spec
- binding the WayWarden design too tightly to one provider’s API surface
- overfitting to code-agent assumptions when WayWarden is EA-first
- loading every skill / MCP tool by default just because the framework supports it

## OSS / implementation direction

For WayWarden, the key is not adopting this stack wholesale.
The key is matching the durable patterns with a Python-first architecture that still keeps provider choice open.

Implementation direction:
- ADR for harness/runtime/client boundaries
- manifest abstraction in app config / domain model
- run checkpoint model in Postgres
- worker sandbox adapter boundary
- selective skills registry
- explicit tool capability and secret-scoping model

## Recommendation

This article should be treated as a **durable architecture signal**, not just research noise.
It should graduate into architecture decisions around:
- control plane vs worker separation
- protocol-first client surfaces
- manifest-driven execution
- durable resumable runs
- isolated subagents
