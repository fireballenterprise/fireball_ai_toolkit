---
name: test
description: Use for running every lint + unit check the repo's toolchains enable — ruff, pylint, yamllint, actionlint, pytest (ktlint / detekt / gradle for Kotlin), plus the toolkit drift gate. Takes --repo <name|path>. Equivalent to /test.
hints:
  - test
instructions:
  - .ai/toolkit/instructions/tests.md
  - .ai/toolkit/instructions/python.md
commands:
  - .ai/toolkit/commands/test.md
---
