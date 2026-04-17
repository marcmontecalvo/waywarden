# Framework Experts Pattern for WayWarden

This document adapts the strongest idea from the Pi Pi concept: a single framework-oriented meta-agent backed by several narrow domain experts that can be queried in parallel.

## Goal

When the work is about **WayWarden itself**, the agent should not rely on one giant vague system prompt.
It should route research through small experts with sharply defined ownership.

## Recommended expert set

- `agent-definition-expert`
- `prompt-expert`
- `capability-expert`
- `config-runtime-expert`
- `extension-expert`

## Why this is useful

- Reduces prompt sprawl
- Keeps answers domain-specific
- Encourages parallel research
- Makes it easier to add new framework surfaces later
- Gives the orchestrator cleaner inputs before planning or building

## Recommended flow

1. User asks for a framework change
2. Orchestrator classifies the request
3. Relevant experts are queried in parallel once
4. Orchestrator synthesizes findings
5. Planner produces an implementation plan
6. Plan-reviewer critiques it
7. Builder implements
8. Reviewer and/or red-team verify
9. Documenter updates docs if needed

## Practical rule

The orchestrator should only consult experts when the task touches framework design, prompt conventions, capability packaging, config/runtime behavior, or plugin/extension surfaces.

For normal feature work inside an app or service, use the worker agents directly.
