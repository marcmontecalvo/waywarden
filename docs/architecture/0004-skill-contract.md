# ADR 0004: Skill contract

## Status
Accepted

## Decision
Skills are code plugins with typed metadata and runtime contracts.

## Required fields
- name
- description
- model profile
- required tools
- required memory scopes
- required knowledge scopes

## Rules
- no skill bypasses approvals
- no skill reaches provider internals directly
- no skill owns the channel layer
