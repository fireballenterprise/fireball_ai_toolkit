---
name: cleanup
description: Clean up a merged feature branch (switch to default, pull, delete it), sweep local build/cache trash, then drop redundant .gitkeep files. A scope (all|ai|dev_prd) does it across that slice of the family.
argument-hint: "[all|ai|dev_prd] [--repo <name|path>]"
agent: agent
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.repo.route "cleanup $ARGUMENTS"`

Three phases, in order:

1. **Branch cleanup** — if the current branch has a merged GitHub PR, switch to the default
   branch, pull, and delete the branch. A protected branch / dirty tree / unmerged PR is a
   warning + skip, not a failure.
2. **Trash sweep** — remove regenerable caches (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`,
   `*.egg-info/`, `.DS_Store`, …) and *orphaned* directories under `modules/` / `tasks/` /
   `tests/` (dirs git tracks no file in — the residue a module move leaves behind). Lists
   everything and asks before deleting. Never touches `topics/` or `tmp/`.
3. **Redundant `.gitkeep`** — `git rm` tracked `.gitkeep` placeholders in directories that now
   hold other tracked content (anywhere below them), so they no longer keep an empty directory
   alive. Lists them and asks first; the deletion is *staged*, not committed — commit it yourself.
   A `.gitkeep` that is still the only tracked file in its directory is left alone.

`/cleanup all` (or `ai` / `dev_prd`) runs both phases in each repo of that scope of
`properties.yml`'s `repos:` family. `/cleanup --repo <name|path>` runs them in one other managed
checkout (mutually exclusive with a scope).
