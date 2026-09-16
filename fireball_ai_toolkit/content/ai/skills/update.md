---
name: update
description: Use for checking dependency, Python, workflow-action, and .sdkmanrc toolchain versions against latest releases and updating the locks — read-only, never installs. Toolchain-aware; takes --repo <name|path> or a leading repo token to target another checkout. Equivalent to /update.
hints:
  - update
  - update <repo>
instructions:
  - .ai/toolkit/instructions/versioning.md
commands:
  - .ai/toolkit/commands/update.md
---
