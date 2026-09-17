---
name: push
description: Push changes to git remote — invoke fix, invoke test, then commit and push. A scope (all|ai|dev_prd) runs the full push across that slice of the family.
argument-hint: "[all|ai|dev_prd] [--repo <name|path>]"
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.repo.route "push $ARGUMENTS"`

Bare `/push` pushes the current repo. `/push all` (or `ai` / `dev_prd`) runs the real `/push`
(invoke fix + invoke test + commit + push) in each repo of that scope — same as
`/repo push <scope>`. Confirm the repo list first, and never skip a repo's tests. `/push --repo
<name|path>` pushes one other managed checkout (mutually exclusive with a scope).
