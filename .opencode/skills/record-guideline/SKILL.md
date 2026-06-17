---
name: record-guideline
description: Record a new technical guideline following strict formatting rules.
---

# Record Guideline

## Required Fields

- Topic
- Principles (1-10, required)
- Pitfalls (2-3, required)
- Decisions (2-3, optional)

## Content Rules

- Imperatives only; project-specific; under 20 lines total.
- No generic explanations or broad best-practice dumps.
- Order: Principles -> Pitfalls -> Decisions.

## Template

    ```markdown
    # <Topic> Guidelines

    ## Principles
    - <Principle 1>
    - <Principle 2>
    ...

    ## Pitfalls
    - <Pitfall 1>
    - <Pitfall 2>
    ...

    ## Decisions
    - <Decision 1>
    - <Decision 2>
    ...
    ```

## Save Rules

1. Slugify topic and save `work/guidelines/<slug>.md`.
2. Update `work/project-config.md` in the appropriate section.
3. Confirm saved path and config update.
