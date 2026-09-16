---
name: add_feature
description: File a feature request as a GitHub Issue on a repo in the family (native Feature type + enhancement label). Alias for /backlog add feature.
argument-hint: --repo <name> --title "..." [--body "..."] | <freeform description>
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.backlog.route "add feature $ARGUMENTS"`

Thin alias for `/backlog add feature`. Follow the **Recognition** and **Issue body format**
sections of [.ai/toolkit/commands/backlog.md](.ai/toolkit/commands/backlog.md): resolve the repo
(ask if ambiguous), write `**Summary:**` then `## Request` then `## Why / details` then
`## Done when`, **scrub secrets**, confirm, then file it.
