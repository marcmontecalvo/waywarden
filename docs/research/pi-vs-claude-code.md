---
type: research
title: "Pi vs Claude Code — Harness Patterns & Gaps for WayWarden"
status: Routed
date: 2026-04-17
source_url: "https://github.com/disler/pi-vs-claude-code"
source_type: repo
priority: directly-relevant
tags: [hooks, extensions, multi-agent, open-source, safety, orchestration, event-lifecycle, extension-composition]
relates_to_adrs: [0004, 0005, 0011]
---

# Pi vs Claude Code — Harness Patterns & Gaps for WayWarden

**Source**: https://github.com/disler/pi-vs-claude-code  
**Context**: Comprehensive comparison of Pi Agent (open-source, minimal, extensible) vs Claude Code (proprietary, batteries-included, safe-by-default)

## What is actually strong here?

### 1. Event & Hook System
Pi exposes 25+ granular in-process TypeScript events that let you intercept, block, and modify behavior at critical lifecycle points:
- `input` — gate all user prompts before agent sees them
- `before_agent_start` — inject per-turn system prompts dynamically
- `agent_start`, `agent_end`, `turn_start`, `turn_end` — granular agent lifecycle tracking
- `tool_call`, `tool_result`, `tool_execution_start/update/end` — real-time tool streaming
- `BashSpawnHook` — intercept bash before process spawns
- `context` — direct access to what's in the context window
- `session_before_fork`, `session_fork`, `session_switch` — session branching/tree support

Claude Code has ~14 hook events, mostly shell-based and out-of-process. Coarser, but more enterprise-friendly.

### 2. Extension Composition
Pi extensions stack (compose multiple `-e` flags in one session), communicate via shared `pi.events` bus, and persist state via `pi.appendEntry()`. Supports ephemeral testing (`pi -e npm:@foo/bar`).

Claude Code plugins are module-based, loaded from config, no inter-plugin communication.

### 3. Multi-Agent Orchestration Patterns
- **Purpose Gate**: Force intent declaration at startup, inject into every agent turn, show persistent widget
- **Dispatcher Pattern**: Lead agent picks specialist and delegates via `dispatch_agent` tool
- **Subagent Widget**: Live progress tracking for parallel sub-agents with `/sub` command
- **Agent Teams**: Team grid dashboard showing all team members and status
- **Agent Chains**: Sequential pipeline where `$INPUT` from agent N becomes agent N+1's prompt

Claude Code has built-in sub-agents and teams (native Task tool), but less extensibility for custom orchestration.

### 4. Dynamic System Prompt Injection
Pi's `before_agent_start` hook allows per-turn system prompt modification, enabling purpose-gate and custom agent behaviors. Claude Code has no equivalent; system prompt is preset.

### 5. Tool Registration & Override
Pi allows extensions to register custom tools via `pi.registerTool()` and override built-ins. Typed event narrowing via `isToolCallEventType()` lets you know which tool is being called. Claude Code and OpenCode support tool hooks but less granularly.

### 6. Session Branching & Tree Format
Pi stores sessions as JSONL with id/parentId (tree structure), enabling fork/branch/explore/switch operations. Claude Code uses linear session model. OpenCode similar to Claude Code.

### 7. Context Window Visibility
Pi's `context` event gives direct access to all messages. You can filter, prune, or audit what gets compacted. Claude Code and OpenCode don't expose this.

### 8. Philosophy & Design Trade-offs
The repo clearly articulates two valid but opposite approaches:
- **Pi**: "If I don't need it, it won't be built. You design your experience." (~200-token system prompt, YOLO by default, in-process extensions, effectively unlimited customization ceiling)
- **Claude Code**: "Batteries-included, safe by default, accessible to all." (~10K-token system prompt, deny-first permissions, out-of-process hooks, bounded customization)

## Why it matters for WayWarden

1. **Approval model decisions**: WayWarden's ADR-0005 commits to explicit policy presets (yolo/ask/allowlist/custom). The repo clarifies what "YOLO" actually means operationally and what escape hatches exist.

2. **Extension architecture**: WayWarden's ADR-0004 defines 13 extension types but doesn't specify execution model (in-process? out-of-process? composable? state?). This repo demonstrates the impact of that choice.

3. **Multi-stage workflows**: WayWarden's agent-workflow spec describes supervisor/worker stages. The repo's purpose-gate, dispatcher, agent-chain, and subagent-widget patterns show concrete implementations worth learning from.

4. **Hooks vs tool execution vs control flow**: WayWarden needs to decide whether extensions can:
   - Intercept input before the agent sees it?
   - Inject dynamic system prompts per-turn?
   - See and modify what's in the context window?
   - Persist state across sessions?
   - Communicate with other extensions?

   This repo's event coverage maps out the full space of possibilities.

5. **Safety & observability**: Pi's philosophy is "if the agent can write and run code, sandbox is mostly theater." Claude Code is "safe by default with deny-first rules." WayWarden's damage-control spec leans Pi's way but should explicitly acknowledge the tradeoffs.

## What should WayWarden borrow?

### Immediately actionable:
1. **Event-driven hook lifecycle**: Document when each event fires, what can block/modify, whether it's async/blocking. Pi's 25+ events are overly granular for WayWarden's first version, but the principle of granular, typed interception is sound.

2. **Input interception**: The `input` event (gate all user prompts before agent processing) is powerful for implementing purpose-gate and custom behaviors. WayWarden should add this to its hook spec.

3. **Per-turn system prompt injection**: Pi's `before_agent_start` is foundational for dynamic behaviors without redefining personas. Borrow this pattern.

4. **Tool execution streaming**: Pi's `tool_execution_start`, `_update`, `_end` enable real-time progress widgets. WayWarden's approval system could use this for operator visibility.

5. **Typed tool narrowing**: When a hook fires on tool execution, knowing *which* tool is being called (bash vs read vs write) enables fine-grained policies. Borrow this from Pi.

6. **Session branching**: Even if WayWarden doesn't ship branching in v1, document the tree-vs-linear session format choice. Pi's JSONL tree is architecturally cleaner for exploration workflows.

7. **Extension composition primitives**: If WayWarden supports multiple extensions, enable them to communicate via an event bus (like Pi's `pi.events`). Define state persistence (`pi.appendEntry()`-like behavior).

8. **Multi-agent routing patterns**: Implement dispatcher and purpose-gate patterns as example extensions, not as built-ins. Demonstrates WayWarden's extensibility.

### Longer-term:
- **Cross-tool standards** (Agent Skills standard): Borrow the namespace/discovery pattern for skills to share across Claude Code, Pi, VS Code, Cursor, etc.
- **Package distribution** (`pi install npm:/git:/local`): Simple, flexible, no marketplace lock-in.

## What should WayWarden explicitly avoid?

1. **Don't ship "safe by default" and "YOLO" as unnamed defaults**: ADR-0005 is right to make policy explicit and presetted. Avoid Claude Code's "deny-first magic" and Pi's "YOLO theater" by being precise.

2. **Don't hide extension state or inter-extension communication**: If extensions exist, they should be able to persist state and talk to each other. Transparency matters.

3. **Don't merge the agent loop with the policy engine**: WayWarden's protocol-first harness (ADR-0011) should keep approval/policy/safety as a separate service, not baked into the agent runtime.

4. **Don't assume a single "agent persona"**: Pi and Claude Code both assume one main agent with sub-agents. WayWarden's supervisor/worker pattern allows true role switching without context leakage. Don't regress to single-persona model.

5. **Don't ship MCP without understanding the cost**: The repo notes MCP adds 7-14K tokens just for the protocol. If WayWarden uses MCP, do so deliberately and measure the impact. Pi avoids it by design; Claude Code ships it by default.

6. **Don't obscure tool execution**: Transparency (see every tool call, token, dollar spent) matters more than hidden optimization. Pi does this well; Claude Code's sub-agents are opaque.

## Is there an OSS path that gets us 70–90% of the value?

**Yes, high confidence.**

- **Pi Agent itself** (MIT, 8.9K stars, Mario Zechner's project): If WayWarden is building a harness, forking or wrapping Pi gets you 25+ events, extension composition, tool streaming, and all the multi-agent patterns immediately. Trade-off: you inherit Pi's philosophy (minimal, extensible, trust engineers to compose their own experience) rather than batteries-included.

- **OpenCode** (104K stars, 735 contributors, open-source Claude Code alternative): Gets you most of Claude Code's UX, MCP, permissions, plan mode, LSP, desktop app, GitHub integration. Trade-off: you inherit Claude Code's philosophy (complete product, safe-by-default, less customization ceiling) and larger codebase to maintain.

- **Hybrid approach**: Build WayWarden's harness layer, adopt Pi's event model and extension composition (smaller surface), but ship damage-control and approval policies from day one (safer than Pi's YOLO, more transparent than Claude Code's deny-first).

**Recommendation for WayWarden**: 
- Study Pi's event/hook architecture and extension composition model; it's architecturally superior for a harness.
- Study Claude Code's safety philosophy and approval workflows; WayWarden's damage-control spec shows you're already doing this well.
- Avoid OpenCode (it's Claude Code, just open-sourced); the innovation is in Pi's minimalism and granular control, not in feature parity.

## Decision points for WayWarden:

1. **Hooks execution model**: In-process TypeScript (Pi) or out-of-process shell (Claude Code)?
2. **Extension composition**: Can extensions stack and communicate, or are they isolated?
3. **State persistence**: Do extensions survive session restarts? How?
4. **Session format**: Linear (SQLite, like Claude Code) or tree (JSONL, like Pi)?
5. **System prompt dynamism**: Fixed at startup, or injectable per-turn?
6. **Default safety philosophy**: Explicit policy presets (you're here), or safe-by-default (Claude Code), or YOLO-first (Pi)?

The pi-vs-claude-code repo clarifies the tradeoffs for each choice. Use it to make informed decisions about WayWarden's harness design.
