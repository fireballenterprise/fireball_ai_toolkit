---
description: Use for pushing to git remote — runs invoke fix, invoke test, then commits and pushes. `/push all` runs the full push in every family repo. Equivalent to /push.
argument-hint: '[all|ai|dev_prd] [--repo <name|path>]'
hints:
- push
- push all repos
- push the repos
instructions:
- .fireball_ai_toolkit/instructions/repos.md
- .fireball_ai_toolkit/instructions/git.md
- .fireball_ai_toolkit/instructions/tests.md
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.repo.route "push $ARGUMENTS"`

Bare `/push` pushes the current repo. `/push all` (or `ai` / `dev_prd`) runs the real `/push`
(invoke fix + invoke test + commit + push) in each repo of that scope — same as
`/repo push <scope>`. Confirm the repo list first, and never skip a repo's tests. `/push --repo
<name|path>` pushes one other managed checkout (mutually exclusive with a scope).
