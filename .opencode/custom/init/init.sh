#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
ROOT_DIR="$(pwd)"
README_TARGET="$SCRIPT_DIR/README.md"
README_LINK="work/README.md"

DIRS=(
  "work"
  "work/stories"
  "work/stories/backlog"
  "work/stories/done"
  "work/stories/in-progress"
  "work/stories/planned"
  "work/ideas"
  "work/ideas/ideas"
  "work/releases"
  "work/adr"
  "work/guidelines"
)

for dir in "${DIRS[@]}"; do
  mkdir -p "$dir"
done

if [ ! -f work/ideas/Inbox.md ]; then
  cat <<'EOF' > work/ideas/Inbox.md
# Inbox
EOF
fi

if [ ! -f work/project-config.md ]; then
  cat <<'EOF' > work/project-config.md
# Project Config

This file is the canonical, human-readable source of truth for repo structure, guideline loading, review triggers, and repo-level command rules.

If another repo document conflicts with this file, follow this file.

## Purpose

- Use this file as rule, not background reading.
- Humans read it to understand expected agent behavior.
- Agents read it to decide which guidelines, reviews, and commands apply.

## Repo Structure

- TODO: Document the top-level repo layout and important domain folders.

## Output Rules

- TODO: Define concise response and formatting rules for agents.

## Domain Rules

- TODO: List each domain, its guideline, matching file patterns, and relevant keywords.

## Technology Rules

- TODO: List key technologies and the guideline file for each.

## Review Rules

- TODO: Define review types, trigger keywords, and linked guideline files.

## Loading Rules

### Always Load

- TODO: List guidelines every agent should always load.

### Analysis

- TODO: Define how agents choose guidelines during analysis.

### Implementation

- TODO: Define how agents choose guidelines from affected files.

### Validation

- TODO: Define how agents choose guidelines and review checks during validation.

## Command Rules

- TODO: List repo-level commands agents should use for validation, codegen, or other required checks.

## Agent Usage Rule

- Read this file first when you need repo structure, guideline loading rules, review triggers, or repo-level command rules.
- Load only the guideline files that match the current task.
- Do not invent rules outside this file, `AGENTS.md`, and the loaded guideline files.
EOF
fi

if [ ! -f AGENTS.md ]; then
  cat <<'EOF' > AGENTS.md
# AGENTS

## Main rule

- Treat files in `work/` as the durable source of truth.
- Start new delivery work with `brainstorm`.
- Prefer repo artifacts over chat memory.

## Important locations

- `work/project-config.md` - repo operating context
- `work/stories/` - story state
- `work/ideas/` - idea capture

## Agent behavior

- Read `work/project-config.md` first.
- Load only guidance relevant to the current task.
- Do not invent repo policy when the repository does not define it.
- Keep workflow decisions and delivery state in repo artifacts.
EOF
fi

if [ -L "$README_LINK" ]; then
  CURRENT_TARGET="$(readlink "$README_LINK")"
  if [ "$CURRENT_TARGET" != "$README_TARGET" ]; then
    echo "Refusing to replace existing work/README.md symlink: points to $CURRENT_TARGET"
    exit 1
  fi
elif [ -e "$README_LINK" ]; then
  echo "Refusing to replace existing work/README.md file; it must remain a symlink to $README_TARGET"
  exit 1
else
  ln -s "$README_TARGET" "$README_LINK"
fi

for dir in "${DIRS[@]}"; do
  if [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ]; then
    touch "$dir/.gitkeep"
  fi
done
