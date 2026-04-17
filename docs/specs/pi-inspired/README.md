# WayWarden Pi-Inspired Agent Pack

This zip contains a **WayWarden-native starter pack** of markdown files and specs derived from the strongest reusable ideas in the `disler/pi-vs-claude-code` repository.

It is **not** a raw mirror of that repo, and it does **not** introduce TypeScript. It converts the most useful prompt/spec patterns into files that should be easy to drop into WayWarden and refine.

## What is in this zip

### 1) Agent prompt files
Location: `.waywarden/agents/`

These are specialist agent definitions adapted for WayWarden:

- `scout.md` — fast read-only repo recon
- `planner.md` — implementation planning
- `plan-reviewer.md` — adversarial plan review before build work
- `builder.md` — implementation worker
- `reviewer.md` — post-build/code review
- `documenter.md` — README/docs cleanup
- `red-team.md` — security/failure-mode review
- `waywarden-orchestrator.md` — meta-agent that routes work to experts/workers

### 2) Expert agent prompt files
Location: `.waywarden/agents/experts/`

These are the higher-value "expert" patterns adapted from `pi-pi` into WayWarden terms:

- `agent-definition-expert.md`
- `prompt-expert.md`
- `capability-expert.md`
- `config-runtime-expert.md`
- `extension-expert.md`

These are intended for building WayWarden itself: agent definitions, prompts, capabilities, runtime config, and extension/plugin surfaces.

### 3) Team definitions
Location: `.waywarden/agents/teams.yaml`

This gives you ready-made team bundles for common flows such as:
- recon/info
- plan-build-review
- full delivery
- framework experts

### 4) Concept/spec docs
Location: `docs/specs/pi-inspired/`

These are implementation-oriented adaptation notes for larger ideas worth bringing into WayWarden later:

- `damage-control.md` — command/path guardrails and destructive-action interception
- `agent-workflow.md` — long-running stateful workflow supervisor pattern
- `agent-forge.md` — dynamic self-expanding tool/capability model
- `framework-experts.md` — meta-agent + expert-team pattern for WayWarden
- `adoption-roadmap.md` — suggested order of implementation

## Where each idea came from

### Core worker agents
These were primarily adapted from:

- `.pi/agents/scout.md`
- `.pi/agents/planner.md`
- `.pi/agents/plan-reviewer.md`
- `.pi/agents/builder.md`
- `.pi/agents/reviewer.md`
- `.pi/agents/documenter.md`
- `.pi/agents/red-team.md`
- `.pi/agents/teams.yaml`

Source repo:
`https://github.com/disler/pi-vs-claude-code/tree/main/.pi/agents`

### Meta-agent + experts pattern
These were primarily adapted from:

- `.pi/agents/pi-pi/pi-orchestrator.md`
- `.pi/agents/pi-pi/agent-expert.md`
- `.pi/agents/pi-pi/prompt-expert.md`
- `.pi/agents/pi-pi/skill-expert.md`
- `.pi/agents/pi-pi/config-expert.md`
- `.pi/agents/pi-pi/ext-expert.md`

Source repo:
`https://github.com/disler/pi-vs-claude-code/tree/main/.pi/agents/pi-pi`

### Larger architecture/spec ideas
These were primarily adapted from:

- `specs/pi-pi.md`
- `specs/damage-control.md`
- `specs/agent-workflow.md`
- `specs/agent-forge.md`

Source repo:
`https://github.com/disler/pi-vs-claude-code/tree/main/specs`

## What was intentionally omitted

I did **not** port these directly because they are too Pi/TUI/theme-specific for a low-friction WayWarden import:

- `theme-expert.md`
- `tui-expert.md`
- `cli-expert.md`
- `keybinding-expert.md`
- `bowser.md`

Those are good references, but not the fastest/highest-confidence lift for WayWarden.

## Suggested placement in WayWarden

This zip assumes the following structure at repo root:

```text
.waywarden/
  agents/
    *.md
    experts/
      *.md
    teams.yaml

docs/
  specs/
    pi-inspired/
      *.md
```

If your repo already has a different conventions folder for agent prompts or specs, move the files accordingly. The file grouping is already separated by purpose.

## Recommended import order

1. Add `.waywarden/agents/` core worker prompts
2. Add `.waywarden/agents/teams.yaml`
3. Add `.waywarden/agents/experts/`
4. Add `waywarden-orchestrator.md`
5. Review `docs/specs/pi-inspired/damage-control.md`
6. Review `docs/specs/pi-inspired/agent-workflow.md`
7. Treat `agent-forge.md` as later-stage

## Notes

- These files are intentionally **more explicit** than the originals.
- They push for stronger output formats, less ambiguity, less over-engineering, and more file/path grounding.
- They are meant to be a practical starting point, not sacred final copies.
