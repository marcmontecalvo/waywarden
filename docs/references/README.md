# WayWarden Pi-Inspired Import Pack (Updated)

This zip is a **WayWarden-oriented starter pack** that pulls in the strongest ideas from several Pi ecosystem repositories without introducing TypeScript or trying to mirror those projects wholesale.

It is organized so you can drop folders into the repo with minimal reshuffling.

## What is in this zip

### 1) Core agent prompts
Location: `.waywarden/agents/`

These are markdown prompt files for specialist workers and orchestration:

- `scout.md` — read-only repo recon and fast fact-finding
- `planner.md` — implementation planning with files, dependencies, and sequencing
- `plan-reviewer.md` — adversarial review of plans before implementation starts
- `builder.md` — implementation worker
- `reviewer.md` — post-build correctness and code-quality review
- `documenter.md` — docs and README maintenance
- `red-team.md` — security, misuse, and failure-mode review
- `waywarden-orchestrator.md` — routes work to workers and experts
- `teams.yaml` — ready-made agent groupings

### 2) Framework expert prompts
Location: `.waywarden/agents/experts/`

These are the highest-value expert-role ideas adapted from the `pi-pi` subteam pattern:

- `agent-definition-expert.md`
- `prompt-expert.md`
- `capability-expert.md`
- `config-runtime-expert.md`
- `extension-expert.md`

These are meant to help WayWarden design and maintain its own framework internals.

### 3) Skill placeholders and integration notes
Location: `.waywarden/skills/`

These are **WayWarden-facing skill directories** based on the most useful skills from `badlogic/pi-skills`. They are not copies of upstream implementation code. They are intentionally thin markdown placeholders that define purpose, usage, expected boundaries, and likely future integration points.

Included skills:

- `brave-search/`
- `browser-tools/`
- `google-calendar/`
- `google-drive/`
- `gmail/`
- `transcribe/`
- `youtube-transcript/`

### 4) Rewind hook integration folder
Location: `.waywarden/hooks/rewind/`

This folder contains markdown implementation notes for adopting the core behavior inspired by `pi-rewind-hook`: lightweight session-safe file rewind / restore checkpoints during coding work.

### 5) Spec and architecture docs
Location: `docs/specs/pi-inspired/`

These are implementation-oriented adaptation docs for larger ideas worth bringing into WayWarden:

- `damage-control.md`
- `agent-workflow.md`
- `agent-forge.md`
- `framework-experts.md`
- `adoption-roadmap.md`
- `skills-integration.md`
- `rewind-hook.md`

### 6) Reference and roadmap docs
Locations:
- `docs/references/external/`
- `docs/research/roadmap/`

These explain what was pulled in now versus what should remain a future research topic.

## Where each group came from

### A. Core worker agents and team pattern
Primarily inspired by:
- `disler/pi-vs-claude-code/.pi/agents/`
- especially `scout.md`, `planner.md`, `plan-reviewer.md`, `builder.md`, `reviewer.md`, `documenter.md`, `red-team.md`, and `teams.yaml`.

### B. Expert-team / meta-agent pattern
Primarily inspired by:
- `disler/pi-vs-claude-code/.pi/agents/pi-pi/`
- especially `pi-orchestrator.md`, `agent-expert.md`, `prompt-expert.md`, `skill-expert.md`, `config-expert.md`, and `ext-expert.md`.

### C. Larger architectural ideas
Primarily inspired by:
- `disler/pi-vs-claude-code/specs/`
- especially `pi-pi.md`, `damage-control.md`, `agent-workflow.md`, and `agent-forge.md`.

### D. Skills worth adding now
Primarily inspired by:
- `badlogic/pi-skills`

That repo provides a clean **skill-as-folder** model and a practical list of high-value agent skills: web search, browser automation, Google Calendar, Google Drive, Gmail, transcription, VS Code integration, and YouTube transcripts. This pack turns the strongest ones into WayWarden-facing placeholder folders and integration docs.

### E. Rewind / rollback behavior worth adding now
Primarily inspired by:
- `nicobailon/pi-rewind-hook`

That repo is specifically about **rewinding file changes during coding sessions**. This pack does not copy its code. Instead, it adds a dedicated WayWarden hook folder and implementation notes so the repo has a clear place for the capability.

### F. Future research / roadmap references
Primarily inspired by:
- `badlogic/pi-share-hf`
- `badlogic/babbletui`

These are not treated as immediate implementation items in this pack. They are documented as future research topics so the ideas are captured without forcing near-term adoption.

## What each file group is for

### `.waywarden/agents/`
Operational prompts for specialist workers and orchestration.

### `.waywarden/agents/experts/`
Prompts for framework-focused experts used when evolving WayWarden itself.

### `.waywarden/skills/`
A stable directory shape for skill modules so WayWarden can grow a skill catalog without redesigning structure later.

### `.waywarden/hooks/rewind/`
A stable home for “checkpoint + restore” work so reversible coding sessions are planned from the start.

### `docs/specs/pi-inspired/`
Concrete translation docs that explain how Pi-inspired concepts should be adapted to WayWarden.

### `docs/references/external/`
Source mapping docs explaining exactly what external repo contributed which idea.

### `docs/research/roadmap/`
Non-committal research items that should be remembered but not forced into current scope.

## Suggested placement in your repo

```text
.waywarden/
  agents/
    *.md
    experts/
      *.md
    teams.yaml
  skills/
    <skill-name>/
      SKILL.md
  hooks/
    rewind/
      README.md
      spec.md

docs/
  specs/
    pi-inspired/
      *.md
  references/
    external/
      *.md
  research/
    roadmap/
      *.md
```

## Recommended import order

1. Add `.waywarden/agents/` and `teams.yaml`
2. Add `.waywarden/agents/experts/`
3. Add `.waywarden/skills/` folder structure
4. Add `.waywarden/hooks/rewind/`
5. Review `docs/specs/pi-inspired/skills-integration.md`
6. Review `docs/specs/pi-inspired/rewind-hook.md`
7. Keep `docs/research/roadmap/` as references until you explicitly choose to pursue them

## Notes

- This pack intentionally favors **structure and prompt/spec clarity** over copied implementation code.
- Nothing here assumes a TypeScript port.
- The goal is to capture the strongest Pi ideas in WayWarden-native form with minimal friction.
