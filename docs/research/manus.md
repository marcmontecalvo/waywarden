---
type: research
title: "Manus — High-Agency Task Orchestration"
status: Captured
date: 2026-04-17
source_url: "https://github.com/manus/manus"
source_type: repo
priority: roadmap
tags: [task-orchestration, artifact-oriented, high-agency]
relates_to_adrs: [0001]
---

# Manus

## Why it is interesting

Manus is a useful reference for **high-agency task execution UX**.
What matters is the feeling that the system can take a messy goal, break it down, work through multiple steps, and produce artifacts with limited hand-holding.

## What appears strong

- End-to-end task framing instead of single-turn prompt framing
- Clear sense of forward progress on multi-step work
- Artifact-oriented execution
- Strong “delegate and continue” product feel

## What WayWarden should borrow

### 1. Goal-to-workflow translation
WayWarden should get better at turning a fuzzy request into:
- a scoped objective
- a short execution plan
- substeps with visible status
- resulting artifacts, messages, or decisions

### 2. Progress visibility
Longer-running work should show:
- what the system decided to do
- what stage it is in
- what artifacts were produced
- where human approval is required

### 3. Artifact-first outputs
The system should bias toward producing concrete outputs:
- draft emails
- task lists
- calendar proposals
- research summaries
- action plans
- handoff packets to other runtimes or agents

## What not to copy

- Unbounded autonomy as a default behavior
- Opaque background action chains
- Product theater that hides uncertainty or failure states

WayWarden should remain more explicit, governed, and approval-aware.

## Best OSS / implementation direction

Look for OSS building blocks that support:
- step/state orchestration
- resumable tasks
- event timelines
- artifact tracking
- approval checkpoints

This is more important than trying to mimic Manus surface UX directly.

## Relevance to WayWarden

High.
This is directly relevant to the EA experience, especially for multi-step personal and executive workflows.

## Recommendation

Treat Manus as a **workflow UX reference**, not an implementation reference.
The near-term takeaway is to improve:
- task state visibility
- execution timelines
- artifact storage
- approval and handoff boundaries
