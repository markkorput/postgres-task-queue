---
description: Record a finished non-feature change as story, branch, and commit
agent: ad-hoc-implementer
---

**Arguments:** `$ARGUMENTS` (optional title hint)

You are the Ad-Hoc Implementer: infer and record one finished, coherent non-feature change from the current git worktree.

## Execute

1. Build the effective change set from current worktree state:
    - include staged and unstaged tracked file changes
    - include untracked files as additions
    - exclude any file named `changes.md` and `Index.md` in any directory
    - exclude any file in `.opencode` directory
2. If the effective change set is empty, stop and return `No eligible changes found (excluding changes.md).`
3. Confirm the effective change set represents one coherent, finished non-feature change:
   - the diff must read as a single fix, refactor, performance improvement, docs update, or chore
   - if the diff appears to contain multiple unrelated changes, stop and say it cannot be recorded as one story
   - if the diff appears to be feature work, stop and say this command only supports non-feature work
4. Ensure you are on a safe branch before creating any files:
   - run `git rev-parse --abbrev-ref HEAD`
   - if the current branch is `HEAD`, `main`, or `master`, create and switch to a new branch before continuing
   - branch name should be derived from `$ARGUMENTS` when provided, otherwise from inferred change intent
5. Reverse-engineer one small-scope story from the effective diff:
    - infer what changed and why it was changed
    - keep scope to fix/perf/refactor/chore-class work only
    - never expand into an epic or broad feature plan
6. Classify story type:
    - `bug` when primary intent is correctness or defect resolution
    - otherwise `chore` or `refactor`, `performance`, `docs`
    - never output `feature` or `spike` for this command
7. Draft story content grounded in the diff using standard sections:
    - title
    - context
    - functional requirements
    - technical requirements
    - acceptance criteria
8. Record the story using `record-story` and save to `work/stories/done/YYYY-MM-DD-<slug>.md`.
9. Before committing, verify the commit scope still matches the inferred story intent:
   - eligible source changes plus the newly recorded story file must still read as one coherent change
   - if additional unrelated changes appeared after story creation, stop and do not commit
10. Commit all resulting changes by following `@.opencode/commands/commit.md` exactly:
    - use a Conventional Commit message (`type: subject`, no scope)
11. Return:
     - eligible files considered
     - excluded files ignored
     - saved story path
     - selected type
     - branch name used
     - commit hash and commit message
     - short rationale linking the diff to the inferred story intent

## Constraints

- Do not modify source code files while running this command.
- Do not discard or move existing git changes.
- Do not continue when the worktree does not represent one coherent finished non-feature change.
- Ignore `changes.md` and `Index.md` content even when present.
- Ignore any file in `.opencode` directory
- Prefer observable facts from the diff over assumptions.
