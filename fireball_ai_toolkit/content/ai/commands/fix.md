---
name: fix
description: Auto-fix lint / format issues for whatever toolchains the repo has (ruff --fix + format, ktlint format, …).
argument-hint: "[--repo <name|path>]"
agent: agent
---

!`uv run --no-sync invoke fix $ARGUMENTS`

Runs every applicable autofixer. `--repo <name|path>` runs it against another managed checkout.
