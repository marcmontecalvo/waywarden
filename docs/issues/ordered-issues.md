---
type: issue
title: "Ordered Issues Backlog"
status: Active
date: 2026-04-17
issue_type: ordered-backlog
priority: execution
phase: harness-core
owner: TBD
target_milestone: "v1-harness"
---

# Ordered issues

1. Bootstrap repo with uv, FastAPI, Ruff, pytest, Alembic
2. Add typed settings and config loader
3. Add health endpoint and structured logging
4. Add instance, profile, and policy concepts to the domain
5. Create domain models: session, message, task, approval, instance, profile
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
22. Implement CLI entrypoint
23. Implement EA profile overlay
24. Implement EA routines: briefing, scheduler, inbox triage
25. Implement delegation envelope support
26. Implement coding profile overlay
27. Implement till-done loop
28. Implement adversarial review routine
29. Implement teams / pipelines / sub-agent execution
30. Implement backup manager and backup route
31. Implement background scheduler
32. Add contract tests
33. Add restore runbook validation
