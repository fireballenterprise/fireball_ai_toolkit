---
name: test
description: Use for running every lint + unit check the repo's toolchains enable — ruff, pylint, yamllint, actionlint, pytest (ktlint / detekt / gradle for Kotlin), plus the toolkit drift gate. Takes --repo <name|path>. Equivalent to /test.
hints:
  - test
instructions:
  - .fireball_ai_toolkit/instructions/tests.md
  - .fireball_ai_toolkit/instructions/python.md
commands:
  - .fireball_ai_toolkit/commands/test.md
---
