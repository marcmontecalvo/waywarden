Parent epic: #<epic-issue-number>

# <phase-id>: <title>

## Goal
<one short paragraph: what this issue accomplishes in operator-visible or agent-visible terms>

## Canonical references
- ADRs: <ADR number(s) this issue is governed by, or `none`>
- Specs: <spec id(s) this issue implements or extends, or `none`>
- Repo paths: <authoritative repo paths that define the contract this issue touches, or `none`>
- Related issues: <#issue-number (title), ...> or `none`

## Scope
- <primary module / file to be created or modified: absolute repo path>
- <behavior to be implemented, stated in terms of the canonical model>
- <config, schema, or migration changes introduced here (including exact `AppConfig` field names if applicable)>
- <implementation stance: sync vs async, pure domain vs adapter vs API route, typed-model flavor (frozen dataclass vs pydantic BaseModel)>

## Non-goals
- <behavior explicitly deferred to another issue, with its phase-id / #issue-number>
- <behavior explicitly out of scope for this phase>

## Canonical model (required for spec-touching issues)
- Exact event / envelope field names used: <verbatim from spec>
- Exact enum values used: <verbatim from spec>
- Exact payload fields used: <verbatim from spec>
- Any spec deviation is a defect in this issue, not a license to diverge.

## Acceptance criteria
- [ ] <criterion stated in terms of the canonical model, verifiable without reading the PR>
- [ ] <criterion stated in terms of the canonical model, verifiable without reading the PR>
- [ ] `mypy --strict` clean for touched packages.
- [ ] No unused imports, no dead code added alongside the change.

## Required tests
- <exact test file path or new file to be created>
- <unit test case, named by behavior>
- <integration test case if applicable, with `@pytest.mark.integration` and Postgres dependency called out>
- <negative test case asserting canonical invariants>

## Blocking dependencies
- <#issue-number <phase-id>: <title>> or `none`
- <#issue-number <phase-id>: <title>>

## Configuration impact
- <exact AppConfig field(s) this issue adds or requires, with type and default>
- `none` if this issue does not touch AppConfig.

## Notes
- <optional clarification that does not reintroduce ambiguity>
- <optional pointer to a specific ADR section or spec section>
