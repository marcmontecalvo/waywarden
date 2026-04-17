---
name: research-intake
description: Parse inbox.md for URLs/references, fetch content, emit properly-formatted research note stubs in docs/research/
---

# Purpose

Turn a line-item inbox of URLs, repo links, and article references into properly-formatted research note files that `research-note-router` can then process.

# Inputs

- `docs/research/inbox.md` containing one entry per line. Each line may be:
  - a bare URL
  - a URL with a short operator note after it (e.g., `https://github.com/x/y - looks relevant to approvals`)
  - a markdown link
- Lines starting with `#` are treated as comments and skipped
- Blank lines are skipped

# Workflow

## Step 1: Parse inbox

Read `docs/research/inbox.md`. Extract every non-comment, non-blank line as a candidate entry. Preserve the operator note if present — it becomes a seed for the "Why it is interesting" section.

## Step 2: Fetch and validate

For each entry:
1. Extract the URL
2. Fetch the URL and verify HTTP 200
3. If the response is less than 500 chars or looks like a login wall, flag as "thin source" and skip
4. Extract: title, primary topic, source_type (repo / article / docs / video / paper)

## Step 3: Generate filename

Convert the primary subject to kebab-case:
- `github.com/coleam00/adversarial-dev` becomes `adversarial-dev.md`
- An article titled "Why Protocols Beat Frameworks" becomes `protocols-beat-frameworks.md`
- Strip common suffixes (`-github`, `-blog`, `-docs`)

## Step 4: Duplicate check

Before writing, check if the filename already exists in `docs/research/`. If yes:
- Do NOT overwrite
- Add the entry to a "duplicates" list for the final report
- Leave the inbox entry in place with a comment noting the existing file

## Step 5: Write the research note

Use this template for every new file:

- Frontmatter fields required:
  - `type: research`
  - `title` as `"{Title} — {one-line summary}"`
  - `status: Captured`
  - `date` as today's date
  - `source_url` as the fetched URL
  - `source_type` as repo | article | docs | video | paper
  - `priority: unassessed`
  - `tags` as 3-5 tags inferred from the fetched content (not from the URL slug)
  - `relates_to_adrs: []`

- Body sections in order:
  - `# {Title}`
  - `## Why it is interesting` — 1-2 sentences synthesized from fetched content; seed with operator note if present
  - `## What appears strong` — 3-5 bullets from fetched content
  - `## Relevance to WayWarden` — leave as "unassessed — run research-note-router to evaluate"
  - `## Source summary` — 3-5 bullet summary of the fetched content

## Step 6: Update inbox

- Remove successfully processed entries
- Keep failed entries (404, thin source, extraction errors) with an inline error comment explaining why
- Keep duplicate entries with a comment pointing to the existing file

## Step 7: Emit report

Report:
- Count of new research notes created, with filenames
- Count of duplicates skipped, with filenames
- Count of failures, with reasons
- Next suggested action: `Run research-note-router on [list of created files]` or `Run research-batch-processor on docs/research/` if 3+ files were created

# Guardrails

- Never overwrite an existing research note
- If URL is inaccessible, leave the entry in inbox.md with an error note; do not create a placeholder file
- Tags must be inferred from actual content, not the URL slug
- If fetched content is less than 500 chars, flag as "thin source" — likely a login wall or 404 returning 200
- Never invent content not present in the fetched source. Leave sections sparse rather than padding.

# Invocation

Typical operator prompt:

`Use research-intake on docs/research/inbox.md`

# Example inbox.md format

```
# Pending research to process

https://github.com/coleam00/adversarial-dev - failure-oriented dev patterns
https://example.com/blog/protocols-over-frameworks
https://github.com/some/repo
```
