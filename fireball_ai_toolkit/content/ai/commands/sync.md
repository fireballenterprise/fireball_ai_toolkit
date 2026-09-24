---
name: sync
description: Sync — pull (auto-resolving lock-file and binary conflicts), then invoke fix, invoke test, commit and push. A scope (all|ai|dev_prd) syncs that slice of the family.
argument-hint: "[all|ai|dev_prd] [--no-tests]"
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

`/sync all` (or `ai` / `dev_prd`) runs the same sync in every repo in that scope of
`properties.yml`'s `repos:` family — each in its own checkout and venv, one confirmation up front,
a summary at the end — same as `/repo sync <scope>`.

For a natural-language request ("sync all repos", "pull and push everything", "sync it up"), run
`uv run --no-sync invoke repo.sync all` for the family or `uv run --no-sync invoke repo.sync` for
this repo. Do not hand-roll git loops.
