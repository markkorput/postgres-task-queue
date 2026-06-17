---
name: record-adr
description: Record a new Architecture Decision Record (ADR) using the date-based naming convention.
---

# Record ADR

## Required Fields

- Title
- Status (default `Proposed`)
- Context
- Decision
- Consequences

## Template

    ```markdown
    # <Title>

    Date: <YYYY-MM-DD>
    Status: <Status>

    ## Context

    <Context>

    ## Decision

    <Decision>

    ## Consequences

    <Consequences>
    ```

## Save Rules

1. Generate date `YYYY-MM-DD`.
2. Slugify title.
3. Save to `work/adr/YYYY-MM-DD-<slug>.md`.
4. Confirm saved path.
