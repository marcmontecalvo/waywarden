---
type: research
title: "Adversarial Dev — Failure-Oriented Development Patterns"
status: Captured
date: 2026-04-17
source_url: "https://github.com/coleam00/adversarial-dev"
source_type: repo
priority: directly-relevant
tags: [testing, adversarial-review, failure-injection, robustness]
relates_to_adrs: [0007]
---

# Adversarial Dev

## Why it is interesting

Adversarial Dev is directly relevant as an OSS reference for **adversarial review, failure injection, and robustness-oriented development workflow**.
That maps well to WayWarden because safety, review quality, and edge-case handling matter more here than flashy autonomy.

## What appears strong

- Adversarial mindset instead of happy-path-only development
- Useful pressure-testing reference for prompts, workflows, and agent behavior
- Likely strong fit for review loops, red-team checks, and system hardening
- Good complement to builder/planner systems that otherwise risk becoming optimistic and undercritical

## What WayWarden should borrow

### 1. Adversarial review as a first-class step
WayWarden should explicitly support review modes that ask:
- what breaks?
- what is unsafe?
- what assumptions are false?
- how can this be abused or misrouted?
- what happens under partial failure?

### 2. Failure-oriented testing prompts
Useful future additions include review prompts and test harnesses for:
- prompt injection attempts
- permission boundary failures
- destructive tool misuse
- malformed memory or knowledge inputs
- broken handoffs between EA, coding, and HA runtimes

### 3. Red-team workflow patterns
This lines up well with the existing idea of a dedicated red-team/reviewer role.
The takeaway is to make those checks systematic, not optional.

## What not to copy

- Security theater without concrete failure models
- Heavyweight process that slows down every iteration unnecessarily
- Adversarial behavior that is disconnected from real operator or runtime risks

## Best OSS / implementation direction

Use this repo as a source of ideas for:
- adversarial prompt packs
- negative test suites
- workflow hardening checklists
- security and misuse review templates

## Relevance to WayWarden

High.
This is especially relevant for:
- tool approval boundaries
- destructive-action policy
- prompt robustness
- runtime separation guarantees

## Recommendation

Keep this in the active research set and connect it later to:
- plan-review prompts
- red-team prompts
- approval engine tests
- integration test scenarios for failure and abuse cases
