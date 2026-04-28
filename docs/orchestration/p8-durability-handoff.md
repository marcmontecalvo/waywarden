---
type: spec
title: "P8 Durability Handoff Metadata"
status: accepted
relates_to_adrs: [0002, 0005, 0006, 0007, 0008, 0011]
---

# P8 Durability Handoff Metadata

P7 teams, pipelines, sub-agents, dispatcher handoffs, till-done loops, and
adversarial-review checkpoints expose metadata seams for P8 durability work.
This document describes how P8 should consume those seams without refactoring
the P7 primitives or coupling them to scheduler, rollback, or escrow code.

## Stable Correlation

P8 checkpoint and resume code should use the provider-neutral `RunCorrelation`
payload fields carried on RT-002 `run.progress` and `run.artifact_created`
events:

- `correlation_id`
- `parent_run_id`
- `child_run_id`
- `dispatcher_run_id`
- `team_run_id`
- `pipeline_run_id`
- `sub_agent_run_id`
- `review_run_id`
- `delegation_id`
- `manifest_run_id`
- `checkpoint_id`
- `saga_id`
- `resume_token`

`checkpoint_id`, `saga_id`, and `resume_token` are optional because P7 can run
without P8 enabled. When supplied, P8 leases and heartbeats should key durable
checkpoint state from `checkpoint_id` and propagate rollback scope through
`saga_id`. `resume_token` is an opaque metadata value for future resume lookups;
P7 must not interpret it.

## Side-Effect Classification

Tool actions may include `tool_actions` metadata. Each action contains:

- `tool_id`
- `action`
- `side_effect.action_class`
- `side_effect.rationale`
- optional `approval_explanation`

The stable side-effect classes are:

- `read-only`
- `workspace-mutating`
- `DB-mutating`
- `provider-mutating`
- `external-write`
- `unknown/high-risk`

P8 retry, DLQ, and saga rollback code should treat `unknown/high-risk` as
non-idempotent unless a later policy layer proves otherwise. P7 only emits the
classification; it does not implement DLQ routing, rollback previews, or
mutation ledgers.

## Token Budget Telemetry

Events may include `token_budget` metadata:

- `budget_id`
- `source`
- `observed_prompt_tokens`
- `observed_completion_tokens`
- `observed_total_tokens`
- `remaining_tokens`
- `warning`

This is telemetry only. P8 token escrow may consume it to build budget leases,
top-up requests, model downgrade decisions, or forced wrap-up triggers, but P7
does not enforce any of those behaviors.

## Approval Explanation

Adversarial, team, and sub-agent tool actions that route through policy or
approval surfaces should include `approval_explanation` metadata with the
policy preset, policy decision details, approval identifiers when present, and
the rationale for the gate. P8 should persist this explanation alongside DLQ
records and saga rollback audit trails so an operator can distinguish a
policy-gated handback from a runtime failure.

## External Events And Saga Rollback

P8 external event ingestion should attach incoming event offsets or high-water
marks as additional metadata alongside the existing correlation fields. P7 does
not define a new RT-002 event type for those offsets.

Saga rollback should use the `saga_id` plus `tool_actions.side_effect` metadata
to decide whether rollback is safe, requires preview, or must be operator
approved. The mutation ledger itself is P8 scope.
