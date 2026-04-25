# Skill: epic-to-tilldone

## Purpose

Convert a GitHub EPIC issue into a TillDone task list, then work through the list until the EPIC is complete.

This skill assumes the Pi `tilldone` extension is loaded.

## Critical TillDone bootstrap rule

`tilldone` blocks non-`tilldone` tools until a list exists and at least one task is in progress.

Therefore, do **not** start by reading files, running `gh`, searching the repo, or inspecting the skill file. First create a bootstrap TillDone list.

Required first actions:

1. Call `tilldone new-list` with a title like:

   ```text
   EPIC bootstrap
   ```

2. Add these bootstrap tasks:

   ```text
   Load repo skill instructions and resolve EPIC reference
   Fetch EPIC from GitHub with gh
   Convert EPIC and child issues into concrete TillDone tasks
   Start the first real EPIC task
   ```

3. Mark the first bootstrap task `inprogress`.

Only after that may you use read, shell, GitHub CLI, or any other tools.

## Required input

An EPIC GitHub issue reference. Accept any of these forms:

- full URL, for example `https://github.com/OWNER/REPO/issues/35`
- issue number, for example `35`
- `OWNER/REPO#35`

If only a number is provided, use the current git repository's GitHub remote.

## Hard rules

- Initialize TillDone before any non-`tilldone` tool use.
- Use `gh` as the source of truth for the EPIC.
- Do not rely only on the EPIC title.
- Read the EPIC body, labels, comments, and linked/mentioned issues where practical.
- Prefer open child issues over closed child issues.
- If the EPIC body defines a required workflow, follow it over this generic workflow.
- Tests are built with each issue, not deferred.
- Do not close the EPIC unless all required child issues/tasks are complete and verified.
- Do not stop after implementation; validate, merge, verify main, close the completed issue, and delete the branch where applicable.
- If a command fails because a `gh --json` field is unsupported, retry immediately with the minimal known-good field set.

## Step 0: Bootstrap TillDone

Before doing anything else, create the bootstrap list:

```text
tilldone new-list
title: EPIC bootstrap
description: Temporary planning list used to unlock tools before reading GitHub/repo state.
```

Add:

```text
Load repo skill instructions and resolve EPIC reference
Fetch EPIC from GitHub with gh
Convert EPIC and child issues into concrete TillDone tasks
Start the first real EPIC task
```

Toggle the first item to `inprogress`.

Then continue.

## Step 1: Resolve repository and EPIC issue

If the user provided a full GitHub issue URL, parse:

- owner
- repo
- issue number

If the user provided only an issue number, determine the GitHub repo from:

```bash
git remote get-url origin
```

Normalize SSH and HTTPS remotes into `OWNER/REPO`.

Examples:

```text
git@github.com:marcmontecalvo/waywarden.git -> marcmontecalvo/waywarden
https://github.com/marcmontecalvo/waywarden.git -> marcmontecalvo/waywarden
```

## Step 2: Read the EPIC

Preferred command:

```bash
gh issue view EPIC_NUMBER \
  --repo OWNER/REPO \
  --json number,title,body,state,url,labels,comments
```

If that fails due to unsupported fields, fall back to:

```bash
gh issue view EPIC_NUMBER \
  --repo OWNER/REPO \
  --json number,title,body,state,url
```

Then fetch comments separately if useful:

```bash
gh issue view EPIC_NUMBER \
  --repo OWNER/REPO \
  --comments
```

Do **not** use unsupported fields like `children` unless the local `gh` version has proven support for them.

## Step 3: Identify child issues and work items

Extract work items in this priority order:

1. Explicit child issue links in the EPIC body.
2. GitHub task list items referencing issues, such as `- [ ] #40`.
3. Issue URLs in the EPIC body or comments.
4. Markdown checklist items.
5. Acceptance criteria sections.
6. Implementation phases or numbered task sections.

For each referenced child issue, read it with:

```bash
gh issue view ISSUE_NUMBER \
  --repo OWNER/REPO \
  --json number,title,body,state,url,labels,comments
```

If `comments` fails, retry without it:

```bash
gh issue view ISSUE_NUMBER \
  --repo OWNER/REPO \
  --json number,title,body,state,url,labels
```

Use issue state to decide whether it is still active.

## Step 4: Replace bootstrap tasks with the real EPIC list

Once the EPIC has been fetched and parsed, clear or replace the bootstrap list using TillDone.

Create a new list with:

```text
title: EPIC #N: <epic title>
description: <short goal summary> Source: <epic URL>
```

Add real tasks.

Recommended task format for child issues:

```text
Issue #40 — <issue title>: implement, test, validate, merge, verify main, close issue
```

Recommended task format for non-issue checklist items:

```text
EPIC checklist — <task text>
```

Recommended task format for acceptance criteria:

```text
Acceptance — <criterion>
```

If child issues exist, prefer one TillDone task per child issue.

If no child issues exist, create tasks from the EPIC sections.

## Step 5: Start the first real EPIC task

After adding real EPIC tasks, immediately mark the first incomplete real task as `inprogress`.

Only after that should implementation begin.

## Step 6: Work each task to completion

For each TillDone task:

1. Understand the relevant issue/spec/acceptance criteria.
2. Create or switch to an appropriate issue branch.
3. Implement tests for the behavior.
4. Implement the code/docs/config changes.
5. Run the required validation commands from the repo instructions.
6. Fix failures until green.
7. Commit the work.
8. Push the branch.
9. Merge to main.
10. Verify main contains the final commit.
11. Close the completed child issue, if applicable.
12. Delete the branch, if applicable.
13. Mark the TillDone task done.
14. Toggle the next TillDone task to `inprogress`.

## Step 7: Finish the EPIC

When all TillDone tasks are done:

1. Re-read the EPIC.
2. Confirm all required child issues/checklist items are complete.
3. Run final validation from main.
4. Add a concise completion comment to the EPIC summarizing:
   - tasks completed
   - validation run
   - commits/branches merged
   - any remaining known limitations
5. Close the EPIC only if completion criteria are satisfied.

## Failure handling

If `gh` is not authenticated:

- Report the auth problem.
- Do not invent tasks from stale memory.
- Tell the user to run:

```bash
gh auth status
gh auth login
```

If the EPIC has no clear child tasks:

- Create a TillDone list from the EPIC body sections.
- Add a first task to clarify/normalize the EPIC into actionable child issues.

If a child issue is blocked:

- Mark the task with a clear blocker note.
- Continue with other unblocked tasks when possible.
- Do not close the blocked issue.

## Required output format

When the real TillDone list is created, summarize:

```text
TillDone list created:
- EPIC: #N <title>
- Tasks added: X
- First task in progress: #1 <task>
```

When the run completes, summarize:

```text
EPIC completion summary:
- Completed tasks:
- Validation:
- Merged branches:
- Closed issues:
- Remaining blockers:
```
