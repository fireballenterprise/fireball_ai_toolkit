---
description: Use for auto-fix requests — every applicable autofixer (ruff --fix + format; ktlint format for Kotlin). Takes --repo <name|path>. Equivalent to /fix.
argument-hint: '[--repo <name|path>]'
hints:
- fix
instructions:
- .fireball_ai_toolkit/instructions/python.md
---

!`uv run --no-sync invoke fix $ARGUMENTS`

Runs every applicable autofixer. `--repo <name|path>` runs it against another managed checkout.
