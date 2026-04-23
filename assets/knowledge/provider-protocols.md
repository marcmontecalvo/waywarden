---
title: Provider Protocols
tags: [architecture, technical]
domain: general
kind: reference
---

# Provider Protocols

Waywarden defines four runtime-checkable Protocol interfaces in `domain/providers/`. All adapters must implement the matching protocol.

## MemoryProvider

```python
@runtime_checkable
class MemoryProvider(Protocol):
    async def write(self, session_id: SessionId, entry: MemoryEntry) -> MemoryEntryRef
    async def read(self, session_id: SessionId, query: MemoryQuery) -> list[MemoryEntry]
```

- `MemoryQuery` carries `session_id`, `query_text`, and `limit`
- `MemoryEntry` carries `session_id`, `content`, `metadata`, `created_at`

## KnowledgeProvider

```python
@runtime_checkable
class KnowledgeProvider(Protocol):
    async def search(self, query: str, *, limit: int = 10) -> list[KnowledgeHit]
    async def fetch(self, ref: str) -> KnowledgeDocument
```

- `KnowledgeHit` carries `ref`, `title`, `snippet`, `score`
- `KnowledgeDocument` carries `ref`, `title`, `content`, `metadata`

## ModelProvider

```python
@runtime_checkable
class ModelProvider(Protocol):
    async def complete(self, prompt: PromptEnvelope, *, tools: Sequence[ToolDecl] = (), stream: bool = False) -> ModelCompletion
```

- `PromptEnvelope` includes `messages`, `memory_block`, `knowledge_block`, `tools`, `system_prompt`
- `ModelCompletion` includes provider identification, token counts, and recording timestamp

## ToolProvider

```python
@runtime_checkable
class ToolProvider(Protocol):
    async def invoke(self, tool_id: str, action: str, params: Mapping[str, object]) -> ToolResult
    def capabilities(self) -> frozenset[str]
```

- `ToolDecl` declares a tool: `tool_id`, `action`, `description`, optional `parameters`
- `ToolResult` carries `tool_id`, `action`, `output`, `success`, optional `error`

## Implementation Pattern

Each adapter sits in `adapters/<name>/` and:
1. Imports ONLY from `domain.providers.types.*` (value types) and `domain.ids`
2. Never imports from sibling adapter directories
3. Implements the Protocol methods (async)
4. Uses `isinstance(provider, <Protocol>)` to verify conformance at construction time
