# ADR 0003: Memory vs knowledge

## Status
Accepted

## Decision
Use Honcho for runtime memory and LLM-Wiki for curated knowledge.

## Memory
Memory is:
- user preferences
- routines
- relationship context
- active project patterns
- inferred habits

## Knowledge
Knowledge is:
- durable notes
- linked docs
- SOPs
- project writeups
- curated references

## Constraints
- memory writes and knowledge ingestion are separate actions
- neither system is the sole database of record for tasks, approvals, or sessions
