---
description: "Use when creating a git branch or drafting a Pull Request for this repo. Covers PR-vs-direct-push, branch naming, and PR description format."
---
# Git & PR Instructions
## PR or direct push?
Check the repo's `pull_request` flag in `properties.yml`'s `repos:` map (`/repo self`). `false` →
this repo ships by committing straight to the default branch, **no PR** — run `invoke fix` +
`invoke test`, fast-forward the default branch to your work, push. `true` → the feature-branch + PR
flow below. `pr_create.py` refuses on a `pull_request: false` repo.

## Branch Naming
- All lowercase, `snake_case` (words separated by `_`)
- 2-4 words describing the change — not a ticket number, not a filename
- End with `_<github_username>` — the author's lowercase GitHub username (get it via
  `gh api user --jq .login`; `gh` is a required tool in this repo)
- Example: `add_branch_naming_rules_lbecker`

## Pull Request Description
- Title: concise summary, under 70 characters
- Body:
  - `## Summary` — 1-3 sentences describing the overall change
  - `## Changes` — a bulleted list of the key changes (one bullet per logical change, not per file)

This is the canonical PR format for this repo — the `pr` / `pr-notes` commands implement it. Those
commands (and every other) are authored once in `.ai/toolkit/commands/` (via
`fireball_ai_toolkit`'s `content/commands/`) and rendered per tool; see
`.ai/toolkit/instructions/ai_commands.md`.

## Pull Request Assignee
Always assign the PR to the user who asked for it — `gh pr create --assignee @me` (the currently
authenticated `gh` user). `modules/toolkit/repo/pr_create.py` does this automatically; if you ever create a
PR by hand (not through that module), pass `--assignee @me` yourself.
