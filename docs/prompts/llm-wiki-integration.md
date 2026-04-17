---
type: prompt
title: "LLM-Wiki Integration"
status: In Use
date: 2026-04-17
prompt_type: system-provider-adapter
used_by: [knowledge-integration]
version: "1.0"
tags: [knowledge, llm-wiki, adapter, integration]
---

Implement a KnowledgeProvider interface and an LLMWikiKnowledgeProvider adapter.

Requirements:
- treat LLM-Wiki as an external compiler/service boundary
- no deep dependency on LLM-Wiki internals
- support search(), ingest(), refresh()
- store provenance metadata
- include a filesystem fallback adapter
