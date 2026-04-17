# Rewind Hook

This folder is the reserved home for a WayWarden rewind / restore capability inspired by `nicobailon/pi-rewind-hook`.

## Purpose

Allow coding sessions to create lightweight restore checkpoints so the agent or user can rewind file changes safely.

## Why this exists

Reversible edits reduce fear, make autonomous edits safer, and create a clean answer to “undo what the agent just changed.”

## Intended scope

- Create checkpoints before significant edits
- Restore to a chosen checkpoint on demand
- Avoid interfering with normal git workflows
- Prefer local, transparent mechanics over magic

See `spec.md` for the adaptation notes.
