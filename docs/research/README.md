---
type: research
title: "Research References Index"
status: Active
date: 2026-04-17
source_url: null
source_type: index
priority: directly-relevant
tags: [research, index, patterns, external-products]
relates_to_adrs: null
---

# Research References

This folder tracks external products, repos, and UX patterns that are worth studying for **specific strengths**.

The goal is **not** to clone products wholesale or import closed-source assumptions into WayWarden.
The goal is to identify:
- what each tool does unusually well
- which parts fit WayWarden's architecture and product direction
- what should remain out of scope
- where an OSS implementation may be a better source than the proprietary product itself

## Current references

### Directly relevant now
- [pi-vs-claude-code](./pi-vs-claude-code.md)
  - Event/hook system architecture (in-process vs out-of-process)
  - Extension composition and multi-agent orchestration patterns
  - Philosophy differences: Pi (minimal/extensible) vs Claude Code (batteries-included/safe-by-default)
  - Design decision framework for WayWarden's harness
- [pi-skills](../references/external/pi-skills.md)
  - File-based skills catalog and skill packaging ideas
- [pi-rewind-hook](../references/external/pi-rewind-hook.md)
  - Rewind/restore checkpoint concept for coding sessions
- [archon](./archon.md)
  - OSS orchestration, workflow-state, and control-plane reference
- [ottomator-agents](./ottomator-agents.md)
  - OSS multi-agent workflow and role-packaging reference
- [adversarial-dev](./adversarial-dev.md)
  - Adversarial review, hardening, and failure-oriented development reference
- [harness-design-long-running-apps](./harness-design-long-running-apps.md)
  - Long-running harness architecture and lifecycle design reference
- [openai-agents-sdk-2026-04-15](./openai-agents-sdk-2026-04-15.md)
  - Harness, sandbox, manifest, durability, and isolated-subagent design signals
- [openai-codex-desktop-2026-04](./openai-codex-desktop-2026-04.md)
  - Protocol-first harness, client/runtime separation, and multi-surface product direction

### Roadmap / research references
- [pi-share-hf](./roadmap/pi-share-hf.md)
  - Session export, redaction, review, and publish pipeline ideas
- [babbletui](./roadmap/babbletui.md)
  - Possible future operator-console / terminal UX reference
- [wisprflow](./wisprflow.md)
  - Dictation-first UX, low-friction capture, and correction flows
- [manus](./manus.md)
  - High-agency task orchestration and artifact-oriented execution UX
- [claude-cowork](./claude-cowork.md)
  - Collaborative coding / coworking workflow patterns
- [claude-code](./claude-code.md)
  - Terminal-native coding agent UX, repo awareness, and approval patterns

## Usage rules

1. Always include a link to the original source doc in the md that is created.
2. Do not treat any proprietary product as the spec.
3. Pull over patterns, not branding or surface mimicry.
4. Prefer architecture-compatible ideas that reduce token bloat, reduce operator friction, or improve safety.
5. Where possible, identify an OSS implementation path before planning product work.
6. Keep notes opinionated and implementation-oriented.
7. When a research note changes how WayWarden should actually be built, graduate that change into `docs/architecture/`.

## Suggested evaluation template

Each reference doc should answer:
- What is actually strong here?
- Why does it matter for WayWarden?
- What should we borrow?
- What should we explicitly avoid?
- Is there an OSS path that gets us 70 to 90 percent of the value?
