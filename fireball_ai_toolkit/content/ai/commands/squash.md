---
name: squash
description: Anchored squash of all commits to the root commit. Prompts to review the message, confirm squash, and optionally force push.
argument-hint: "[--repo <name|path>]"
agent: agent
---

!`uv run --no-sync invoke repo.squash $ARGUMENTS`
