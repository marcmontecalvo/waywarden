# ADR 0007: Good and bad patterns

## Good
- adapters everywhere
- typed config
- domain/provider separation
- multi-instance support
- profile-driven behavior
- shared root-level assets with metadata filters
- approvals as first-class objects
- boring persistence
- token accounting in the core loop
- global tracing abstraction with no-op mode
- background reflection jobs only when explicitly backlog-scheduled

## Bad
- giant god prompt
- direct provider types in the domain layer
- channels executing tools
- dream system in hot path
- profile-specific forks of the harness
- overbuilt distributed architecture
- autonomous HA mutation
- forking OpenClaw or Hermes and deleting until it hurts less
- hidden policy behavior instead of explicit presets
