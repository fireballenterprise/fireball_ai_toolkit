---
name: add_bug
description: File a bug as a GitHub Issue on a repo in the family (native Bug type + bug label). Alias for /backlog add bug.
argument-hint: --repo <name> --title "..." [--body "..."] | <freeform description>
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.backlog.route "add bug $ARGUMENTS"`

Thin alias for `/backlog add bug`. Follow the **Recognition** and **Issue body format** sections
of [.ai/toolkit/commands/backlog.md](.ai/toolkit/commands/backlog.md): resolve the repo from what
the user said (ask if the fuzzy match is ambiguous), craft a clean title + a verbose repro body,
transcribe any pasted screenshot into the body, **scrub secrets**, confirm, then file it.
