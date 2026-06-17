---
name: record-idea
description: Record a single idea or a grouped themed idea file under work/ideas/ideas.
---

# Record Idea

## Supported Formats

This skill supports two formats:

1. Single idea file
2. Grouped themed idea file

Choose the grouped themed format when multiple ideas belong together by theme or review context.

## Required Fields

### Single idea file

- Title
- What
- Why
- Notes

### Grouped themed idea file

- Title
- Scope
- Theme
- Idea entries

Each idea entry must include:

- Title
- Why it matters
- Evidence
- Impact
- Recommended next step

Optional when helpful:

- Existing related idea
- Confidence

## Template

### Single idea file

    ```markdown
    # <Title>

    Last updated: <Last updated date>

    ## What
    <What>

    ## Why
    <Why>

    ## Notes
    <Notes>
    ```

### Grouped themed idea file

    ```markdown
    # <Theme> Ideas - <scope>

    Last updated: <Last updated date>

    ## Scope

    - Target: <whole repo or provided scope>
    - Theme: <theme>
    - Basis: <key files or directories reviewed>
    - Existing idea check: <files consulted for dedupe>

    ## Ideas

    ### <Idea title>

    - Why it matters: <why>
    - Evidence: <repo-grounded evidence with file paths>
    - Impact: <impact>
    - Recommended next step: <next step>
    - Existing related idea: <optional>
    - Confidence: <optional>
    ```

## Save Rules

1. Generate `YYYY-MM-DD` and readable "Last updated" date.
2. Slugify the title or `theme-scope` pair.
3. Save to `work/ideas/ideas/YYYY-MM-DD-<slug>.md`.
4. For grouped themed files, prefer filenames like `YYYY-MM-DD-<theme>-<scope>.md`.
5. Confirm saved path.

## Decision Rules

1. Use a single idea file when the artifact is one standalone concept.
2. Use a grouped themed file when multiple related ideas came from one review or belong to one theme.
3. Do not mix unrelated themes in one grouped file.
4. Prefer a small number of coherent files over one giant mixed file.
