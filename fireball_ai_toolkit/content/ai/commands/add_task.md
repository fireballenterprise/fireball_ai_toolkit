---
name: add_task
description: File a task (chore / cross-cutting work) as a GitHub Issue on a repo in the family (native Task type + task label). Alias for /backlog add task.
argument-hint: --repo <name> --title "..." [--body "..."] | <freeform description>
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.backlog.route "add task $ARGUMENTS"`

Thin alias for `/backlog add task`. Follow the **Recognition** and **Issue body format** sections
of [.ai/toolkit/commands/backlog.md](.ai/toolkit/commands/backlog.md): resolve the repo (ask if
ambiguous), write `**Summary:**` then `## Request` then `## Why / details` then `## Done when`,
**scrub secrets**, confirm, then file it.
