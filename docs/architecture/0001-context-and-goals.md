# ADR 0001: Context and goals

## Status
Accepted

## Problem
The user needs a real executive-assistant runtime, not a generic single-agent sandbox and not a fused house/coding mega-agent.

## Decision
Build an EA-first harness as a small native Python service with clean adapter boundaries.

## Goals
- omnichannel EA interaction
- persistent memory
- curated knowledge
- task tracking
- tool calling with approvals
- future handoff to HA and coding runtimes

## Non-goals
- HA runtime internals
- coding runtime internals
- universal autonomous agent framework
- self-editing governance
- dream system in the request hot path
