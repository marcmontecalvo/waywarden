# Chunking Rules

Use these rules to split planning docs into execution issues.

## Good issue size
A good child issue:
- has one clear outcome
- can be implemented and reviewed in one focused run
- has acceptance criteria that can be verified concretely
- has a small enough surface area that adversarial review is practical

## Split when
Split work into separate issues when any of these are true:
- different areas of the codebase move independently
- different acceptance criteria would make review muddy
- one part is pure scaffolding while another is runtime behavior
- one part is cleanup and another is new feature work
- one part blocks the other and the dependency should be explicit

## Do not split too far
Avoid issues that are too tiny, such as:
- renaming-only issues unless they are risk-heavy
- docs-only issues that belong tightly to the implementation slice
- separate issues for tests when the tests are part of the same implementation truth

## Preferred shape
Prefer:
- phase-scoped issue ids like `P1-1`, `P1-2`
- ordered EPIC checklist
- explicit blocking dependencies
- explicit non-goals
- required tests written into the issue body
