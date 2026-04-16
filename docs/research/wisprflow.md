# Wispr Flow

## Why it is interesting

Wispr Flow is a useful reference for **dictation-first UX** rather than classic chat UX.
The interesting part is not voice AI branding. The interesting part is how little friction exists between thought and text entry.

## What appears strong

- Fast capture with minimal ceremony
- Good correction loop after imperfect transcription
- UX that treats voice as a primary input path, not a novelty add-on
- Low cognitive overhead compared with opening a chat tool and composing a prompt manually

## What WayWarden should borrow

### 1. Frictionless capture paths
WayWarden should eventually support ultra-fast intake flows for:
- quick notes
- reminders
- task creation
- follow-up capture
- rough-draft email/message capture

The key lesson is that **latency and interruption cost matter more than feature count**.

### 2. Post-capture correction loop
If the user speaks a messy note, the system should help repair it quickly:
- confirm intent only when needed
- allow lightweight rewrite/cleanup passes
- preserve the raw original when appropriate

### 3. Context-aware insertion targets
A strong future UX would let capture land directly into:
- inbox triage queue
- task inbox
- calendar follow-up queue
- research scratchpad
- routine suggestion queue

## What not to copy

- Generic “AI dictation” positioning
- Voice everywhere for its own sake
- Heavy client-side complexity before core EA value exists

## Best OSS / implementation direction

Prefer an internal capture pipeline built on:
- local or low-latency STT
- a cleanup/rewrite pass
- explicit target routing
- audit-friendly storage of raw + cleaned text

This should be treated as a **future UX layer** on top of the EA core, not as a blocker for the current harness.

## Relevance to WayWarden

High for future operator UX.
Low for immediate EA-core milestone work.

## Recommendation

Keep this as a research reference and revisit when:
- base task and note ingestion are stable
- voice intake becomes a first-class channel
- latency budgets for input handling are being optimized
