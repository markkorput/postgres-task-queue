# AiFact Flow

Artifact-based AI workflow for disciplined software delivery.

AiFact is a repo-local framework for using AI in software delivery without relying on hidden chat state. It keeps context, decisions, work state, and handoffs in repository artifacts so the workflow stays explicit, reviewable, and durable.

Repository: https://github.com/arminc/aifact

## Why it exists and core ideas

Experienced engineers do not start each task from zero. They already know the repository structure, local rules, project history, common failure modes, and what is still underspecified.

AI usually does not.

That gap is why AiFact exists. Instead of relying on long chat history, hidden memory, or prompt luck, AiFact stores working context in repository artifacts so model behavior is durable and reviewable.

- Artifacts on disk are the source of truth.
- `work/` holds durable project context, story state, ideas, ADRs, and release artifacts.
- Reviews, decisions, and handoffs happen through repo files.
- Agents have narrow roles with explicit handoffs instead of one general-purpose coding role doing everything.
- Validation is a gate, not a courtesy step.

This makes AI-assisted delivery more auditable, repeatable, and maintainable across sessions, contributors, and model upgrades.

## Why not just use a generic coding agent and a long chat?

A generic coding agent plus long chat can be fast for one-off tasks.

It becomes unreliable when delivery spans multiple sessions or people, because the key state lives mostly in conversation context that is hard to review, diff, hand off, or enforce.

AiFact addresses that by moving the operating context into repo artifacts and running work through explicit phases with validation gates. The result is less prompt repetition, clearer ownership, and higher confidence that work can be resumed and audited later.

## How it works

The normal delivery path starts by clarifying the work, records that understanding in a story, then moves through analysis, implementation, validation, and closeout.

1. Start with `brainstorm` to clarify what should be built.
2. Record the result as a durable artifact with `record-story`.
3. Run delivery phases such as analysis, implementation, and validation against that artifact.
4. Close the loop with done-state and PR workflows after validation passes.

## What is in this repo

- `.opencode/` contains the workflow implementation: agents, commands, skills, scripts, and bootstrap assets.
- `work/` contains durable repo-local artifacts that guide AI behavior and preserve delivery history.
- `docs/` contains the detailed framework reference.

## Documentation

- `docs/overview.md` - framework concepts and rationale
- `docs/getting-started.md` - onboarding and first-run path
- `docs/workspace.md` - what `work/` is for and how it is structured
- `docs/agents.md` - agent roles and responsibilities
- `docs/commands.md` - command entry points
- `docs/skills.md` - reusable skills
- `docs/flows.md` - story flow, delivery loop, and artifact flow
- `docs/prompting.md` - prompt reference file notes

If you only remember one rule, remember this one: start with `brainstorm`, and treat the artifact on disk as the source of truth.
