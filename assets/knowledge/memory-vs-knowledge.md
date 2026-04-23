---
title: Memory vs Knowledge
tags: [architecture, design]
domain: general
kind: concept
---

# Memory vs Knowledge (ADR-0003)

## Overview

In Waywarden, memory and knowledge are kept as **separate concerns** with distinct provider implementations. This separation follows principle ADR-0003.

## Memory

Memory is:
- User preferences and routines
- Relationship context
- Active project patterns
- Inferred habits
- Recent durable context

Memory is stored per-session and backed by the Honcho service by default. Access is scoped to specific sessions via `SessionId`.

## Knowledge

Knowledge is:
- Durable notes and linked documents
- SOPs and project writeups
- Curated references
- Indexed source material

Knowledge is stored in a shared directory (`assets/knowledge/`) across profiles. Profiles filter but do not clone.

## Provider Boundary

Memory and knowledge providers must NOT import from each other. This is enforced by a static import check in tests:

```python
# tests/adapters/memory/test_memory_knowledge_isolated.py
def test_no_cross_imports():
    memory_mod = importlib.import_module("waywarden.adapters.memory.fake")
    source = open(memory_mod.__file__).read()
    assert "adapters.knowledge" not in source
```

## Switching Providers

Each subsystem supports multiple providers:
- Memory: `fake` (in-memory), `honcho` (remote service)
- Knowledge: `filesystem` (local markdown), `llm_wiki` (LLM-Wiki service)

Selection is done via `AppConfig` — no refactoring required.
