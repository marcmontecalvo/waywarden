---
title: Getting Started
tags: [quickstart, tutorial]
domain: general
kind: guide
---

# Getting Started

Welcome to Waywarden — the core harness for multi-profile intelligent agent systems.

## Installation

Install Waywarden using uv:

```bash
git clone https://github.com/marcmontecalvo/waywarden.git
cd waywarden
uv sync
```

## Configuration

Waywarden uses a profile-driven configuration. The default `ea` (executive assistant) profile provides:

- Memory access via Honcho
- Knowledge base via LLM-Wiki
- Model routing via Claude or fake provider

Set your environment variables:

```bash
export WAYWARDEN_ACTIVE_PROFILE=ea
export WAYWARDEN_MODEL_ROUTER=fake
```

Start the dev server:

```bash
make dev
```

## Profiles

Waywarden ships with multiple profiles in the `profiles/` directory:

- **ea** — Executive assistant, focused on memory and knowledge
- **coding** — Development helper, focused on code review and implementation
- **home** — Home automation, integrated with Home Assistant

Each profile is selection from the same core harness — no code changes needed.

## Next Steps

- Read the [architecture decisions](https://github.com/marcmontecalvo/waywarden/tree/main/docs/architecture) for design rationale
- Check the [contributing guide](https://github.com/marcmontecalvo/waywarden/blob/main/docs/contributing.md) for workflow conventions
