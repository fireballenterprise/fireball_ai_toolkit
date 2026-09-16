---
name: upgrade
description: Install the toolchain upgrades reviewed via /update — refresh the uv binary, install the pinned Python + rebuild .venv, uv sync --upgrade, and the .sdkmanrc toolchain.
argument-hint: "[<repo>] [uv | python | libs | sdkman] [--repo <name|path>]"
agent: agent
---

# upgrade — install the upgrades reviewed via /update
Performs the actual installs after you've reviewed the config changes with `/update`.

## Usage
Every applicable upgrade (interactive):
!`uv run --no-sync python -m modules.toolkit.versioning.route "upgrade $ARGUMENTS"`

`$ARGUMENTS` may name one toolchain (`uv` / `python` / `libs` / `sdkman`), and/or start with a
repo selector — a family-repo name or a path, or `--repo <name|path>` (same as `/update`). Add
`--sync` for just `uv sync --upgrade` with no version check.

## What it does (only for the toolchains the repo has)
- uv: refresh the `uv` binary itself (unpinned — `brew upgrade uv`, or `uv self update`)
- Python: install the pinned version, rebuild `.venv`
- libs: `uv sync --upgrade`
- sdkman: `sdk env install` (installs whatever `.sdkmanrc` pins)

## Workflow
1. `/update` — review + rewrite config files
2. `git diff` — check what changed
3. `/upgrade` — install

## Exit codes
- 0: success (or nothing needed) · 1: error · 2: cancelled
