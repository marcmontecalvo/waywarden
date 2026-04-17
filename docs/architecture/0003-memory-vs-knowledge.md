# ADR 0003: Memory vs knowledge

## Status
Accepted

## Decision
Keep memory and knowledge as separate concerns and make both provider-driven.

## Memory
Memory is:
- user preferences
- routines
- relationship context
- active project patterns
- inferred habits
- recent durable context

## Knowledge
Knowledge is:
- durable notes
- linked docs
- SOPs
- project writeups
- curated references
- indexed source material

## Starting providers
- Memory: Honcho
- Knowledge: LLM-Wiki

## Rule
These are starting providers, not permanent architecture commitments.

Switching providers should be a configuration change, not a refactor.

## Constraints
- memory writes and knowledge ingestion are separate actions
- neither system is the sole database of record for tasks, approvals, sessions, or policy
- provider-specific types must not leak into the domain layer
