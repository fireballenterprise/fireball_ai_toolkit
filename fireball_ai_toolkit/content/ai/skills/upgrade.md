---
name: upgrade
description: Use for installing the toolchain upgrades reviewed via /update — refresh the uv binary, install pinned Python + .venv rebuild, uv sync --upgrade, .sdkmanrc toolchain. Toolchain-aware; takes --repo <name|path> or a leading repo token. Equivalent to /upgrade.
hints:
  - upgrade
  - upgrade <repo>
instructions:
  - .ai/toolkit/instructions/versioning.md
commands:
  - .ai/toolkit/commands/upgrade.md
---
