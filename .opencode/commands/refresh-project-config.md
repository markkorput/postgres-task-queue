---
description: Refresh work/project-config.md from current repo state
agent: brainstorm
---

# Refresh Project Config

**Arguments:** `$ARGUMENTS` (optional focus hint)

Update `work/project-config.md` directly so it matches the current repository as closely as possible without inventing new policy.

## Execute

1. Read and use these files first:
   - `work/project-config.md`
   - `AGENTS.md`
2. Inspect the current repository state relevant to project config:
   - top-level repo directories
   - `work/guidelines/`
   - `work/stories/`
   - `work/adr/`
   - `docs/`
   - `Makefile`
   - any domain folders explicitly referenced by the current config
3. Update `work/project-config.md` in place.
4. Refresh only what can be verified from the repo. Prioritize these sections:
   - `Repo Structure`
   - `Technology Rules`
   - `Command Rules`
   - guideline file references in `Domain Rules` and `Review Rules`
5. Preserve existing wording and intent when it is still compatible with the repo.
6. If a detail cannot be safely inferred from repo artifacts, keep the current text instead of inventing a new rule.
7. If the repo clearly contains a new durable structure or rule source, add it concisely.
8. After editing, return:
   - whether `work/project-config.md` changed
   - the main updates applied
   - any ambiguous areas that were intentionally left unchanged

## Constraints

- Auto-update `work/project-config.md`; do not stop for approval.
- Do not modify files outside `work/project-config.md`.
- Do not invent new domains, review triggers, or keyword lists unless they are directly supported by current repo artifacts or clearly extend an existing verified pattern.
- Prefer minimal edits over rewrites.
- Keep the file concise and human-readable.
- If `$ARGUMENTS` is provided, use it only as a hint for where to look more closely; still refresh the whole file.
