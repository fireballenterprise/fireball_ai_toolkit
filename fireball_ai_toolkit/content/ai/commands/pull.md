---
name: pull
description: Pull updates from git remote — stash, pull with rebase, restore stash. A scope (all|ai|dev_prd) pulls that slice of the family; --repo <name|path> pulls one other checkout.
argument-hint: "[all|ai|dev_prd] [--repo <name|path>]"
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.repo.route "pull $ARGUMENTS"`

Bare `/pull` rebases the current branch. `/pull all` (or `ai` / `dev_prd`) switches each repo in
that scope of `properties.yml`'s `repos:` family to its verified default branch and
`pull --ff-only`s it — same as `/repo pull <scope>`. `/pull --repo <name|path>` pulls one other
managed checkout (mutually exclusive with a scope).
