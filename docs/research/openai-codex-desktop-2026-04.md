---
type: research
title: "OpenAI Codex Desktop Expansion (2026-04) — Multi-Surface Harness Design"
status: Analyzed
date: 2026-04-17
source_url: "https://venturebeat.com/technology/openai-drastically-updates-codex-desktop-app-to-use-all-other-apps-on-your-computer-generate-images-preview-webpages)"
source_type: product
priority: directly-relevant
tags: [protocol-first, multi-client, harness-architecture, persistent-state]
relates_to_adrs: [0002, 0011]
---

# OpenAI Codex desktop expansion (2026-04)

## What is actually strong here?

The important signal is not “desktop app features are flashy.”
The important signal is that the same harness is being surfaced through more than one client:
- desktop
- web
- IDE / terminal-adjacent flows
- browser preview
- image generation
- remote devbox / SSH workflows
- background work with continuity
- preference memory

## Why it matters for WayWarden

WayWarden should not be built as “the dashboard app with an agent behind it.”
It should be built as:
- a core harness/runtime
- a stable protocol / event surface
- multiple possible clients on top

That matters even before v1 because UI choices harden fast.

## What we should borrow

### 1. Protocol-first design
The harness should expose a stable internal protocol for:
- runs
- events
- approvals
- task state
- artifacts
- resumptions
- client reconnects

### 2. Server-side continuity
Runs should continue even if a UI disconnects.

Borrow:
- reconnectable clients
- durable server-side state
- append-only event history
- resumable job views

### 3. Multi-surface readiness
Even if v1 only ships with one primary UI, the harness should assume future clients such as:
- dashboard
- CLI / operator console
- mobile-friendly surface
- future desktop surface
- future integrations with HA and coding runtimes

### 4. Layered memory
Separate:
- run-local scratch state
- project memory
- user preferences
- reusable skills / playbooks
- policy and approval history

### 5. Mixed workflow support
The harness should be able to support more than “edit code and run commands.”
Over time, flows may include:
- browsing / preview
- artifact creation
- image generation
- multi-step operator review
- handoff between runtimes

## What we should avoid

- making the dashboard the source of truth
- tightly coupling internal run logic to one UI
- assuming all future work is code-centric
- treating desktop/computer-use as a near-term requirement for the EA core

## Security / operational implication

If WayWarden ever grows into desktop or computer-use territory, it should require:
- strict local permission boundaries
- narrow credential scope
- audit logs
- explicit approvals
- revocable integrations
- clean separation between orchestration and local execution

## Recommendation

This should stay primarily in `research/` for now, but its durable parts should influence architecture immediately:
- protocol-first harness design
- client/runtime separation
- durable server-side run state
- layered memory
- multi-surface readiness without premature UI sprawl
