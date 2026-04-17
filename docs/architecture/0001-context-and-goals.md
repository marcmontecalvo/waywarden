# ADR 0001: Context and goals

## Status
Accepted

## Problem
The project started as an EA-first runtime, but the better long-term architecture is a slim, reusable harness core that can run multiple profiles and multiple instances side by side.

## Decision
Build Waywarden as a **small core harness** with:
- extension loading
- profile packs
- instance overlays
- explicit policy
- swappable providers
- API-first boundaries

## Goals
- support multiple instances at once
- support multiple profiles on the same core
- keep the core small and boring
- support persistent memory
- support curated knowledge
- support task tracking and tool calling
- support profile-specific widgets, routines, teams, and pipelines
- support future handoff to external runtimes where useful
- keep token bloat observable and controllable

## Non-goals
- giant universal autonomous agent OS
- UI-specific architecture
- autonomous HA mutation
- self-editing governance
- dream/reflection system in the request hot path
- overbuilt distributed architecture
