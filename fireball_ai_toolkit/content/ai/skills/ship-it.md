---
description: Use for pushing the current feature branch and opening a Pull Request in one step. Equivalent to /ship-it. Also triggered by the phrases "punch it", "punch it chewy", or "ship it".
argument-hint: no arguments required
hints:
- make it so
- hit it number one
- punch it
- punch it chewy
- ship it
instructions:
- .fireball_ai_toolkit/instructions/git.md
- .fireball_ai_toolkit/instructions/repos.md
- .fireball_ai_toolkit/skills/push.md
- .fireball_ai_toolkit/skills/pr.md
- .fireball_ai_toolkit/skills/pr-notes.md
---

First check how this repo ships:

!`uv run --no-sync python -m modules.fireball_ai_toolkit.repo.route "self"`

**If `pull_request: false`** — this repo does **not** use PRs. Run `invoke fix` + `invoke test`
(must pass), then switch to the default branch, `git merge --ff-only <your feature branch>`,
`git push origin <default>`, and delete the feature branch. Report the pushed commit. Stop here.

**If `pull_request: true`** — run the push workflow:

!`uv run --no-sync python -m modules.fireball_ai_toolkit.repo.route "pr_push"`

If it fails, show the full output, explain which stage failed, and ask how to proceed — do not
continue to the PR steps below.

Then follow the full `/pr` flow (see `.fireball_ai_toolkit/skills/pr.md`): gather the branch/diff context
via `uv run --no-sync python -m modules.fireball_ai_toolkit.repo.route "pr_diff"`, write a `## Summary` and
`## Changes` description, find-or-file the tracking issue, then create the PR with
`uv run --no-sync python -m modules.fireball_ai_toolkit.repo.route "pr_create --title=\"<title>\" --content=\"<notes>\" --issue=<N>"`
(omit `--issue` if none was resolved). Report the PR URL and the linked issue, if any. If
`use_ci: false`, CI won't run — the local `invoke test` was the gate.
