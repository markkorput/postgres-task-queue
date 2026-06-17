---
name: record-story
description: Record a new user story using the story template.
---

# Record Story

## Required Fields

- Title
- Type (`feature|bug|chore|spike`)
- Context
- Functional Requirements
- Technical Requirements (approach, decisions, rejected alternatives, constraints)
- Acceptance Criteria

## Template

    ```markdown
    # <Title>

    ## Type

    <Type>

    ## Context

    <Context>

    ## Functional Requirements

    <Functional Requirements>

    ## Technical Requirements

    <Technical Requirements - Include implementation approach, libraries/tools chosen, technical decisions with rationale, state management, API integration, validation requirements>

    ## Acceptance Criteria

    <Acceptance Criteria>
    ```

## Save Rules

1. Generate date `YYYY-MM-DD`.
2. Slugify title.
3. Save to `work/stories/backlog/YYYY-MM-DD-<slug>.md`.
4. Confirm saved path.
