Implement a MemoryProvider interface and a HonchoMemoryProvider adapter.

Requirements:
- async methods
- separate read/write/consolidate methods
- no Honcho-specific types in domain layer
- configuration via config/memory.yaml
- unit tests with a fake provider
- integration tests skippable without credentials
