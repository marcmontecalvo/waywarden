---
type: issue
title: "Ordered Issues Backlog (Historical)"
status: Deprecated
date: 2026-04-17
issue_type: ordered-backlog
priority: execution
phase: harness-core
owner: marcmontecalvo
target_milestone: "v1-harness"
---

> **Deprecated.** Issue tracking moved to GitHub on 2026-04-17.
> See [README.md](README.md) and https://github.com/marcmontecalvo/waywarden/issues.
> This file is retained only as the original flat ordering that informed phase-by-phase sub-issue creation.

# Ordered issues

1. Bootstrap repo with uv, FastAPI, Ruff, pytest, Alembic
2. Add typed settings and config loader
3. Add health endpoint and structured logging
4. Add instance, profile, and policy concepts to the domain
5. Create domain models: session, message, task, approval, instance, profile
   - Add run, event, checkpoint, and workspace-manifest models so durable execution is not encoded only in transport or worker code
   - Keep manifest and run-state types provider-neutral and owned by the domain layer
6. Create SQLAlchemy models and Alembic migration
7. Implement repositories
8. Define provider protocols: model, memory, knowledge, tool, channel, tracer
9. Define extension base contract and registry
10. Define profile overlay contract and loader
11. Add root-level shared asset folders and metadata schema
12. Implement model router
13. Implement approval engine and policy loader
14. Add explicit policy presets: yolo, ask, allowlist, custom
15. Implement token accounting hooks
16. Implement tracer abstraction with OTel and no-op modes
17. Implement Honcho adapter + fake adapter
18. Implement LLM-Wiki adapter + filesystem fallback
19. Implement context builder
20. Implement tool registry
21. Implement chat route and orchestration service
   - Add explicit stage transitions for `intake -> plan -> execute -> review -> handoff/complete`
   - Persist operator-visible progress, artifacts, and approval checkpoints in the orchestration record
   - Return enough run state for clients to reconnect without rebuilding the task narrative from scratch
   - Expose append-only run events so CLI, web, and future client surfaces can render the same server-side truth
   - Carry resumptions, artifact links, and event history through one protocol-first run surface instead of UI-specific endpoints
22. Implement CLI entrypoint
23. Implement EA profile overlay
24. Implement EA routines: briefing, scheduler, inbox triage
25. Implement delegation envelope support
   - Include objective, constraints, non-goals, acceptance criteria, and artifact context in every envelope
   - Support specialist handoff metadata for dispatcher/team patterns without leaking full upstream context by default
   - Record lightweight checkpoints so delegated work can hand back plan-approved, implementation-complete, and review-found-issues states
26. Implement coding profile overlay
   - Filter in coding-handoff, repo-aware iteration, and approval-visibility behaviors without hardwiring them into the harness core
   - Keep coding-session continuity and artifact-linked conversation references in profile-owned assets
27. Implement till-done loop
   - Bias the loop toward concrete artifacts, visible progress, and explicit operator intervention points rather than opaque autonomy
   - Surface plan revisions, check results, and handback summaries as first-class loop outputs
28. Implement adversarial review routine
   - Add failure-oriented review passes for prompt injection, approval-boundary misuse, malformed memory/knowledge inputs, and destructive tool misuse
   - Produce a reusable checklist and test fixture set for negative-path review, not just prompt prose
   - Keep adversarial review systematic and scoped to real runtime/operator risks
29. Implement teams / pipelines / sub-agent execution
   - Support dispatcher/team workflow packaging with normalized handoff artifacts and visible per-agent progress
   - Keep specialist roles explicit, bounded, and composable instead of collapsing into one opaque persona
   - Reuse pipeline primitives for chained execution and review checkpoints without coupling them to a single provider model
30. Implement backup manager and backup route
31. Implement background scheduler
   - Run queued, resumable background work with explicit state transitions and retry visibility
   - Keep background jobs inspectable from the control plane and separate from request-path orchestration
   - Support scheduled wake-up for long-running work that resumes against durable run state instead of ad hoc job-local memory
32. Add contract tests
33. Add restore runbook validation
