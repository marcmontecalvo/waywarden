# Repo intelligence checklist

Use this before large-repo implementation work.

- [ ] Estimate repo/task complexity.
- [ ] Decide whether CodeGraph is worth using.
- [ ] If available and worth it, index or refresh the repo.
- [ ] If needed, start the CodeGraph MCP server.
- [ ] Use CodeGraph for architecture tracing and cross-file impact analysis.
- [ ] Validate any touched-file conclusions against the real files.
- [ ] Fall back to normal git/filesystem/search if CodeGraph is missing, stale, or not worth the setup cost.
