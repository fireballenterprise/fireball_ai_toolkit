---
name: ship-it
description: Ship the current branch — PR + push for pull_request:true repos, or fast-forward + direct push to the default branch for pull_request:false.
argument-hint: no arguments required
agent: agent
---

First check how this repo ships:

!`uv run --no-sync python -m modules.toolkit.repo.route "self"`

**If `pull_request: false`** — this repo does **not** use PRs. Run `invoke fix` + `invoke test`
(must pass), then switch to the default branch, `git merge --ff-only <your feature branch>`,
`git push origin <default>`, and delete the feature branch. Report the pushed commit. Stop here.

**If `pull_request: true`** — run the push workflow:

!`uv run --no-sync python -m modules.toolkit.repo.route "pr_push"`

If it fails, show the full output, explain which stage failed, and ask how to proceed — do not
continue to the PR steps below.

Then follow the full `/pr` flow (see `.ai/toolkit/commands/pr.md`): gather the branch/diff context
via `uv run --no-sync python -m modules.toolkit.repo.route "pr_diff"`, write a `## Summary` and
`## Changes` description, find-or-file the tracking issue, then create the PR with
`uv run --no-sync python -m modules.toolkit.repo.route "pr_create --title=\"<title>\" --content=\"<notes>\" --issue=<N>"`
(omit `--issue` if none was resolved). Report the PR URL and the linked issue, if any. If
`use_ci: false`, CI won't run — the local `invoke test` was the gate.
