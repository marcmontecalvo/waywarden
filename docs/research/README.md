# Research References

This folder tracks external products, repos, and UX patterns that are worth studying for **specific strengths**.

The goal is **not** to clone products wholesale or import closed-source assumptions into WayWarden.
The goal is to identify:
- what each tool does unusually well
- which parts fit WayWarden's architecture and product direction
- what should remain out of scope
- where an OSS implementation may be a better source than the proprietary product itself

## Current references

### Directly relevant now
- [pi-vs-claude-code](./pi-vs-claude-code.md)
  - Specialist-agent prompt pack
  - Meta-expert routing pattern
  - Planning/review/build workflow ideas
- [pi-skills](./pi-skills.md)
  - File-based skills catalog and skill packaging ideas
- [pi-rewind-hook](./pi-rewind-hook.md)
  - Rewind/restore checkpoint concept for coding sessions

### Roadmap / research references
- [pi-share-hf](./pi-share-hf.md)
  - Session export, redaction, review, and publish pipeline ideas
- [babbletui](./babbletui.md)
  - Possible future operator-console / terminal UX reference
- [wisprflow](./wisprflow.md)
  - Dictation-first UX, low-friction capture, and correction flows
- [manus](./manus.md)
  - High-agency task orchestration and artifact-oriented execution UX
- [claude-cowork](./claude-cowork.md)
  - Collaborative coding / coworking workflow patterns
- [claude-code](./claude-code.md)
  - Terminal-native coding agent UX, repo awareness, and approval patterns

## Usage rules

1. Do not treat any proprietary product as the spec.
2. Pull over patterns, not branding or surface mimicry.
3. Prefer architecture-compatible ideas that reduce token bloat, reduce operator friction, or improve safety.
4. Where possible, identify an OSS implementation path before planning product work.
5. Keep notes opinionated and implementation-oriented.

## Suggested evaluation template

Each reference doc should answer:
- What is actually strong here?
- Why does it matter for WayWarden?
- What should we borrow?
- What should we explicitly avoid?
- Is there an OSS path that gets us 70 to 90 percent of the value?
