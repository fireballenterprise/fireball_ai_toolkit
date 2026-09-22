---
name: sync
description: Sync this repo — pull (auto-resolving lock-file and binary conflicts), then invoke fix, invoke test, commit and push. This repo only; no family scope.
argument-hint: "[--no-tests]"
agent: agent
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.repo.route "sync $ARGUMENTS"`

`/sync` is `/pull` followed by `/push` in one step, for the moment a pull has diverged and you want
it settled and shipped rather than handled by hand. It stashes, pulls, and falls back to
`pull --rebase` when the branches have diverged. Conflicts are resolved automatically only where
there is a safe answer:

- previously recorded resolutions (`git rerere`)
- binary files and lock files take the incoming version, because regenerating is the fix for both

Anything else stops the sync, aborts the rebase and restores the stash, so nothing is half-applied.
Then it runs `invoke fix` and `invoke test` and commits and pushes, exactly as `/push` does. It
refuses to push unless the tests pass; `--no-tests` exists but should not be the habit.

It acts on the current repo only. For the whole family, run `/pull all` then `/push all`.
