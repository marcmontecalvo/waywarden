---
type: setup
title: "Provider Setup"
status: Active
date: 2026-04-27
tags: [setup, providers, honcho, llm-wiki, anthropic]
---

# Provider Setup

Waywarden uses swappable providers for model inference, memory, and knowledge.
All providers default to a `fake` (in-process stub) implementation so that
local development never requires external services.

## Environment variable precedence

```
process env (WAYWARDEN_* prefix)
  > .env file in CWD
    > config/app.yaml
      > AppConfig class defaults
```

## Model provider

| Variable | Values | Default |
|---|---|---|
| `WAYWARDEN_MODEL_ROUTER` | `fake`, `anthropic` | `fake` |
| `WAYWARDEN_ANTHROPIC_API_KEY` | your key | — |
| `OPENAI_API_KEY` | your key | — |
| `OLLAMA_BASE_URL` | endpoint | `http://127.0.0.1:11434` |

### Fake provider (default)

No configuration needed. The fake router returns deterministic stub responses.
Use this for unit tests and offline development.

### Anthropic provider

```dotenv
WAYWARDEN_MODEL_ROUTER=anthropic
WAYWARDEN_ANTHROPIC_API_KEY=sk-ant-...
```

Requires the `anthropic` extra:

```bash
uv sync --extra anthropic
```

### Failure modes

- Missing `WAYWARDEN_ANTHROPIC_API_KEY` with `model_router=anthropic` →
  startup error.
- Anthropic API rate-limit or network error → run transitions to `failed`
  state with the error attached to the terminal event.

## Memory provider (Honcho)

| Variable | Values | Default |
|---|---|---|
| `WAYWARDEN_MEMORY_PROVIDER` | `fake`, `honcho` | `fake` |
| `HONCHO_BASE_URL` | endpoint | `http://127.0.0.1:8787` |
| `HONCHO_API_KEY` | your key | — |

### Fake provider (default)

In-process stub. Memory is not persisted across restarts.

### Honcho provider

Honcho is a purpose-built memory service. Run it locally or point at a hosted
instance.

```dotenv
WAYWARDEN_MEMORY_PROVIDER=honcho
HONCHO_BASE_URL=http://127.0.0.1:8787
HONCHO_API_KEY=your-honcho-key
```

Requires the `honcho` extra:

```bash
uv sync --extra honcho
```

### Failure modes

- Honcho unreachable at startup → server starts but memory operations will
  error at runtime. EA tasks requiring memory context will fail or degrade
  gracefully depending on policy.
- Invalid `HONCHO_API_KEY` → 401 from Honcho; run degrades to no-memory mode.

## Knowledge provider (LLM-Wiki)

| Variable | Values | Default |
|---|---|---|
| `WAYWARDEN_KNOWLEDGE_PROVIDER` | `filesystem`, `llm_wiki` | `filesystem` |
| `WAYWARDEN_KNOWLEDGE_FILESYSTEM_ROOT` | path | `assets/knowledge` |
| `LLM_WIKI_WORKSPACE` | path | `./data/knowledge` |
| `LLM_WIKI_CLI` | binary name | `llm-wiki` |
| `LLM_WIKI_ENDPOINT` | endpoint | — |
| `LLM_WIKI_API_KEY` | your key | — |

### Filesystem provider (default)

Reads markdown files from `assets/knowledge/`. No external service required.
Suitable for development and for inspecting knowledge without LLM-Wiki.

### LLM-Wiki provider

LLM-Wiki indexes and serves curated knowledge (SOPs, project writeups, source
code). Configure it when you need semantic search over a larger knowledge base.

```dotenv
WAYWARDEN_KNOWLEDGE_PROVIDER=llm_wiki
LLM_WIKI_ENDPOINT=http://127.0.0.1:9000
LLM_WIKI_API_KEY=your-llm-wiki-key
```

### Failure modes

- `LLM_WIKI_ENDPOINT` not set with `knowledge_provider=llm_wiki` → config
  error at startup.
- LLM-Wiki unreachable → knowledge queries return empty results; EA tasks
  proceed with no knowledge context.

## Tracing (OpenTelemetry)

| Variable | Values | Default |
|---|---|---|
| `WAYWARDEN_TRACER` | `noop`, `otel` | `noop` |
| `WAYWARDEN_TRACER_ENDPOINT` | OTLP endpoint | — |

The `noop` tracer is a zero-overhead stub. Switch to `otel` and point at a
collector (Jaeger, Grafana Tempo, etc.) when you need distributed traces.

```dotenv
WAYWARDEN_TRACER=otel
WAYWARDEN_TRACER_ENDPOINT=http://localhost:4318/v1/traces
```

Requires the `otel` extra:

```bash
uv sync --extra otel
```

## Policy preset

| Variable | Values | Default |
|---|---|---|
| `WAYWARDEN_POLICY_PRESET` | `yolo`, `ask`, `allowlist`, `custom` | `ask` |
| `WAYWARDEN_POLICY_OVERRIDES_PATH` | path to policy file | — |

- `yolo` — auto-allow all tool invocations (no approval gates)
- `ask` — require explicit approval at approval checkpoints
- `allowlist` — allow only whitelisted actions; deny everything else
- `custom` — load policy from `WAYWARDEN_POLICY_OVERRIDES_PATH`

## Local dev defaults summary

For fully offline development, the only required variable is:

```dotenv
WAYWARDEN_DATABASE_URL=postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden_dev
```

All providers default to fake stubs. `make db-up` + `make migrate` +
`make run` is sufficient to bring up a working local instance.
