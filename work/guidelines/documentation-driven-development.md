# Documentation-Driven Development Guidelines

## Principles
- **Specs as functional blueprints**: Documentation must describe *what* the system does, not *how* it does it. Focus on functional behavior, inputs, outputs, and edge cases.
- **Always up-to-date**: Specs must reflect the latest functional behavior, including bug fixes and edge cases.
- **Actionable**: Specs must include clear functional requirements, examples, and failure modes to guide implementation.
- **Story-driven**: Specs are created, updated, and validated as part of story workflows (analysis, implementation, validation).
- **Minimal overhead**: Spec updates are scoped to the story and avoid unnecessary churn.

## Pitfalls
- **Implementation leakage**: Specs that describe *how* the system works (e.g., internal APIs, data structures) rather than *what* it does.
- **Incomplete specs**: Missing edge cases, failure modes, or examples.
- **Stale specs**: Out-of-date specs that no longer match the functional behavior.
- **Over-specification**: Documenting trivial details or internal refactors.
- **Ambiguity**: Vague or high-level specs that fail to serve as a functional blueprint.

## Decisions

### 1. Spec Focus
- Specs **must** describe functional behavior only (e.g., inputs, outputs, edge cases, failure modes).
- Specs **must not** include implementation details (e.g., internal APIs, data structures, algorithms).
- Implementation details belong in **ADRs** or inline code comments.

### 2. When to Create/Update Specs
- **New features**: Stories must include an initial spec outline during drafting. The spec must be finalized before implementation starts.
- **Bug fixes**: Stories must check existing specs and update them to include:
  - New edge cases or failure modes discovered.
  - Examples demonstrating the fix.
- **Behavioral changes**: Stories must update specs to reflect changes in functional behavior.
- **Internal refactors**: No spec updates unless functional behavior changes.

### 3. Spec Completeness
Specs must include:
- **Functional Requirements**: A clear, itemized list of what the feature *must* do (e.g., "The task queue must support FIFO ordering").
- **Inputs/Outputs**: Expected inputs and outputs, including types and constraints.
- **Edge Cases**: Functional edge cases and expected behavior (e.g., "If the task queue is full, new tasks must be rejected").
- **Failure Modes**: How the feature fails and how it handles failures (e.g., "If the database connection fails, tasks must be retried").
- **Examples**: Code snippets or scenarios demonstrating usage.
- **Dependencies**: Other features or systems it interacts with.

### 4. Spec Structure
- **Location**: `docs/specs/<feature>.md` (e.g., `docs/specs/task-queue-api.md`).
- **Template**:
  ```markdown
  # <Feature> Spec

  ## Overview
  - Purpose: <Why this feature exists>
  - Dependencies: <Other features/systems it relies on>

  ## Functional Requirements
  - [ ] <Requirement 1> (e.g., "The task queue must support task prioritization")
  - [ ] <Requirement 2>
  - [ ] <Requirement 3>

  ## Inputs/Outputs
  - **Inputs**:
    - <Input 1>: <Description, type, constraints>
    - <Input 2>: <Description, type, constraints>
  - **Outputs**:
    - <Output 1>: <Description, type>
    - <Output 2>: <Description, type>

  ## Edge Cases
  - <Edge case 1>: <Expected behavior>
  - <Edge case 2>: <Expected behavior>

  ## Failure Modes
  - <Failure mode 1>: <How it fails and how it is handled>
  - <Failure mode 2>: <How it fails and how it is handled>

  ## Examples
  ```python
  # Example usage demonstrating functional behavior
  ```

  ## Open Questions
  - <Unresolved functional decisions or tradeoffs>
  ```

### 5. Story Workflow Integration
- **Analysis**: Identify which specs need updates (e.g., "Add edge case for task timeouts").
- **Implementation**: Include spec creation/updates in the story’s technical requirements.
- **Validation**: Verify that specs are up-to-date with the functional behavior and any new information from the story.

### 6. Scope of Spec Updates
- **New features**: Require a new spec.
- **Bug fixes**: Update specs to add edge cases, failure modes, or examples.
- **Behavioral changes**: Update specs to reflect new functional behavior.
- **Internal refactors**: No spec updates unless functional behavior changes.