Implement a KnowledgeProvider interface and an LLMWikiKnowledgeProvider adapter.

Requirements:
- treat LLM-Wiki as an external compiler/service boundary
- no deep dependency on LLM-Wiki internals
- support search(), ingest(), refresh()
- store provenance metadata
- include a filesystem fallback adapter
