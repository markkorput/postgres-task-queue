---
description: Create a Conventional Commit from current changes
agent: lightweight-command-runner
---

You MUST execute the following steps exactly and in order.
Do NOT explain, analyze, plan, or add extra steps.

1. Run `git status --short`.
2. If there are no changes, stop and output `No changes to commit.`
3. Run `git rev-parse --abbrev-ref HEAD`.
4. If the current branch is `HEAD`, `main`, or `master`, stop and output `Refusing to commit on detached HEAD or main/master.`
5. Run `git add -A`.
6. Run `git diff --cached --name-only`.
7. If any staged path matches a likely secret file pattern (`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials*.json`, `secrets*.json`), stop and output `Refusing to commit likely secret files.`
8. If any staged path is under `backend/src/api/v1/` or `backend/src/schemas/`, and no staged path is under `frontend/src/lib/openapi/`, stop and output `Backend API changes detected; run make openapi before committing.`
9. Run `git diff --cached`.
10. If there are no staged changes, stop and output `No changes to commit.`
11. Write one concise Conventional Commit message in the format `type: subject` with:
   - allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
   - no scope
   - imperative, lowercase subject
   - max 72 characters
   - no trailing period
12. Commit using `git commit -m "<message>"`.
13. Run `git status`.

Use the `bash` tool only.
Output only command results. No commentary.
