---
type: prompt
title: "Honcho Integration"
status: In Use
date: 2026-04-17
prompt_type: system-provider-adapter
used_by: [memory-integration]
version: "1.0"
tags: [memory, honcho, adapter, integration]
---

Implement a MemoryProvider interface and a HonchoMemoryProvider adapter.

Requirements:
- async methods
- separate read/write/consolidate methods
- no Honcho-specific types in domain layer
- configuration via config/memory.yaml
- unit tests with a fake provider
- integration tests skippable without credentials
