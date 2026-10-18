---
description: File a feature request as a GitHub Issue on a repo in the family (native Feature type + enhancement label). Alias for /backlog add feature.
argument-hint: --repo <name> --title "..." [--body "..."] | <freeform description>
hints:
  - add_feature
  - add feature
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.backlog.route "add feature $ARGUMENTS"`

Thin alias for `/backlog add feature`. Follow the **Recognition** and **Issue body format**
sections of [.fireball_ai_toolkit/skills/backlog.md](.fireball_ai_toolkit/skills/backlog.md): resolve the repo
(ask if ambiguous), write `**Summary:**` then `## Request` then `## Why / details` then
`## Done when`, **scrub secrets**, confirm, then file it.
