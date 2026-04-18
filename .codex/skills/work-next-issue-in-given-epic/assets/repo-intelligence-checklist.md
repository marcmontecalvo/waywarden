# Repo intelligence preflight

Use this before implementation.

1. Inspect repo size, language mix, and task shape.
2. If CodeGraph or another repo-intelligence index is available and useful for this task, use it.
3. If indexing is unavailable, unsupported, or not worth the overhead, fall back to normal repo exploration.
4. Never trust index-only results blindly; open and verify every touched file directly before editing.
5. Do not block the task on repo indexing.
