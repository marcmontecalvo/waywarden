# Optional CodeGraph preflight

Use CodeGraph opportunistically, not as a hard dependency.

Use it when:
- the repo is medium/large
- the task is architectural tracing, impact analysis, or cross-file refactor work

Skip or de-prioritize it when:
- the repo is tiny
- the task is highly localized
- indexing overhead is not worth it
- the environment does not have CodeGraph ready

Even when CodeGraph is available:
- confirm touched files manually before editing
- do not let indexing failure stop the run
