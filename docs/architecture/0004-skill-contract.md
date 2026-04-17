# ADR 0004: Extension contract

## Status
Accepted

## Decision
Waywarden uses a typed extension model, not a skills-only model.

## Supported extension classes
- widget
- command
- prompt
- tool
- skill
- agent
- team
- pipeline
- routine
- policy
- theme
- context_provider
- profile_overlay

## Required metadata
Each extension should declare at least:
- id
- type
- description
- tags
- allowed profiles
- required tools
- required context
- optional UI surfaces

## Rules
- no extension bypasses policy or approvals
- no extension reaches provider internals directly
- no extension owns the channel layer
- shared assets live once at the repo root and are filtered into profiles
- new extension classes should be addable later without reworking the whole harness
