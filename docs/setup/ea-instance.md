---
type: setup
title: "EA Instance Configuration"
status: Active
date: 2026-04-27
tags: [setup, instances, profiles, ea]
---

# EA Instance Configuration

Waywarden separates *profiles* (what a harness can do) from *instances*
(a specific configured deployment of a profile). One core runtime can serve
multiple instances simultaneously.

## How profiles work

Profiles live in `profiles/{id}/profile.yaml`. Each profile declares:

- which extension types are active (widgets, commands, tools, routines, etc.)
- which providers are required (model, memory, knowledge, channel)
- asset filter rules (e.g., `by_tag: ea` restricts assets to EA-tagged ones)

Three profiles ship with the repo:

| id | Display name | Purpose |
|---|---|---|
| `ea` | Executive Assistant | Personal EA with memory, knowledge, inbox triage |
| `coding` | Coding Agent | Coding tasks, no routines or pipelines |
| `home` | Home | Home Assistant companion |

To list loaded profiles:

```bash
uv run waywarden list-profiles
```

## How instances work

An *instance* binds a profile to a specific deployment with its own
environment overrides and config overlays. Instances are declared in two files:

### 1. Instance manifest — `config/instances.yaml`

```yaml
instances:
  - id: marc-ea
    display_name: Marc EA
    profile_id: ea
    config_path: instances/marc-ea.yaml
```

Each entry needs:
- `id` — unique identifier used in API calls
- `display_name` — human-readable name
- `profile_id` — must match a directory in `profiles/`
- `config_path` — relative to `config/`, points to the overlay file

### 2. Per-instance overlay — `config/instances/<id>.yaml`

```yaml
env: {}
overrides: {}
```

- `env` — instance-specific environment variable overrides (can override
  provider keys, feature flags, etc.)
- `overrides` — instance-specific config overrides (future use)

## The default instance: marc-ea

The repo ships with `marc-ea` pre-configured. It uses the `ea` profile with
default providers (fake model, fake memory, filesystem knowledge for local dev).

To verify it loads:

```bash
uv run waywarden list-instances
# id             display_name  profile_id  config_path
# marc-ea        Marc EA       ea          instances/marc-ea.yaml
```

## Adding a new instance: lisa-ea

1. Add an entry to `config/instances.yaml`:

```yaml
instances:
  - id: marc-ea
    display_name: Marc EA
    profile_id: ea
    config_path: instances/marc-ea.yaml
  - id: lisa-ea
    display_name: Lisa EA
    profile_id: ea
    config_path: instances/lisa-ea.yaml
```

2. Create the overlay file `config/instances/lisa-ea.yaml`:

```yaml
env: {}
overrides: {}
```

Add instance-specific env vars under `env:` if Lisa's instance needs different
provider credentials or policy settings:

```yaml
env:
  WAYWARDEN_POLICY_PRESET: ask
  HONCHO_API_KEY: lisa-specific-honcho-key
overrides: {}
```

3. Verify:

```bash
uv run waywarden list-instances
```

Both `marc-ea` and `lisa-ea` should appear.

## How profile selection works at runtime

When a request arrives at `POST /chat`, the harness selects an instance based
on context. Today, instance routing is stub-level — the `instance-stub` ID is
used as a placeholder. Full multi-instance routing is planned for a later phase.

The active profile can also be set via config:

```yaml
# config/app.yaml
active_profile: ea
```

Or via environment:

```bash
WAYWARDEN_ACTIVE_INSTANCE=marc-ea
```

## Instance loading rules

- If `config/instances.yaml` is missing or malformed → startup fails with an
  explicit config error.
- If a `config_path` overlay file is missing → instance loading fails.
- If a `profile_id` references a profile that doesn't exist in `profiles/` →
  instance loading fails.
- Errors are reported at startup, not at first request.
