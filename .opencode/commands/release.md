---
description: Create a release from done stories
agent: build
model: mistral/codestral-latest
---

# Release Command

Create a new release from stories in `work/stories/done/`.

## Inputs

- Optional version override: `$ARGUMENTS`

## Execute

1. Check whether `work/releases/releases.md` exists.
2. If it exists, read it and determine the latest version from the first table row.
3. If it does not exist, treat this as the first release with no prior version and create `work/releases/releases.md` when writing the release.
4. If the file exists but the releases table is missing, empty, or the first version cannot be parsed as `x.y.z`, stop and ask the user to fix `work/releases/releases.md` first.
5. List story files in `work/stories/done/`, ignore `.gitkeep`, and sort the remaining filenames ascending.
6. If no story files exist, stop and output: `No stories in work/stories/done/.`
7. Read each done story directly using `read`, starting with only the first 12 lines.
8. Extract story metadata without helper scripts:
   - Title: use the first non-empty line that starts with `# `, removing the leading `# `.
   - Type: if a `## Type` section exists, use the next non-empty line before the next heading; otherwise treat type as unknown.
   - Fallback title: filename slug converted to title case.
   - Do this for every done story so the release can list all moved stories.
   - Do not read the full story by default.
   - Only if a title is too vague to support a concise release summary, read more of that story, up to the first 40 lines total, to gather minimal additional context.
   - Do not create Python, Node, shell, or temporary parsing scripts just to read markdown metadata.
9. Propose the next semantic version using these rules:
   - If this is the first release and `$ARGUMENTS` is not a valid `x.y.z`, recommend `0.1.0`.
   - `major`: only if a story title or body explicitly indicates a breaking change, removal, rename, incompatible behavior, or equivalent wording.
   - `patch`: if every story is clearly a fix, docs, chore, refactor, or internal improvement based on extracted type and title/body text.
   - `minor`: otherwise.
   - Use `## Type` as a semver hint when present, but rely on title/body wording for the final decision.
10. Decide final version:
    - If `$ARGUMENTS` is a valid `x.y.z`, use it as the final version.
    - Otherwise ask the user, recommending the proposed version.
    - The user always decides the final version.
11. If `work/releases/<final-version>/` already exists, stop and output: `Release <final-version> already exists.`
12. Create `work/releases/<final-version>/`.
13. Move all done story files into `work/releases/<final-version>/` using `git mv`.
14. Create `work/releases/<final-version>/release.md` with:
   - Title: `# Release <final-version>`
   - A short paragraph summarizing what was built based on the extracted titles and types.
   - If needed, use only the minimal additional context gathered from step 6 for stories with vague titles.
   - Keep the paragraph concise and high level, similar in tone and length to existing release notes.
   - Section `## Stories`
   - Bullet list for each moved story in the sorted order: `- [<title>](./<filename>.md)`
15. Update `work/releases/releases.md`:
    - If the file does not exist, create it with:
      - `# Releases`
      - blank line
      - `| Version | Date | Summary |`
      - `| --- | --- | --- |`
      - `| [<final-version>](./<final-version>/release.md) | <YYYY-MM-DD> | <short release note> |`
    - If the file exists, insert a new row directly under the table header:
      - `| [<final-version>](./<final-version>/release.md) | <YYYY-MM-DD> | <short release note> |`
16. Keep existing rows unchanged.
17. Output:
    - proposed version
    - final version
    - moved files count
    - paths to updated files

## Constraints

- Use tools: `read`, `glob`, and `bash`.
- Do not modify or rewrite existing release folders.
- Do not commit unless the user explicitly asks.
