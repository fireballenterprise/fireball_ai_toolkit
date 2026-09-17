---
name: rebase
description: Rebase current branch onto the remote default branch. Optionally runs squash first before rebasing.
argument-hint: "[--repo <name|path>]"
agent: agent
---

!`uv run --no-sync invoke repo.rebase $ARGUMENTS`
