---
description: Create or update a project guideline following strict formatting rules
agent: brainstorm
---

# Create Guideline Command

**Topic:** `$ARGUMENTS`

Facilitate a short brainstorm to produce or refine a guideline and then record it via `record-guideline`.

## Steps

1. Confirm topic and read `work/project-config.md` for project context.
2. Check `work/guidelines/` for an existing guideline that matches the topic.
3. Decide action:
   - update the existing guideline when the topic materially overlaps an existing guideline
   - create a new guideline when the topic is distinct enough to stand alone
   - if multiple existing guidelines appear to match, ask exactly one targeted question before proceeding
4. Gather content iteratively in this order:
   - Principles (required)
   - Pitfalls (required)
   - Decisions (optional)
5. Keep content imperative, project-specific, under 20 lines, no generic explanations.
6. Rewriting or restructuring the full guideline is allowed when updating if it produces a clearer final guideline.
7. When user confirms, invoke `record-guideline` and record the result.
8. Return:
   - action taken: `created` or `updated`
   - resulting file path
