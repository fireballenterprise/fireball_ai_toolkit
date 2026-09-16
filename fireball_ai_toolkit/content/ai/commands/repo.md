---
name: repo
description: Repo and repo-family operations — list the family map, pull/push/cleanup this repo or a family scope, or apply a change across the family.
argument-hint: list | pull [all|ai|dev_prd] | push [all|ai|dev_prd] | cleanup [all|ai|dev_prd] | <verb> --repo <name|path> | apply <description>
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.repo.route "$ARGUMENTS"`

`/repo` with no subcommand prints usage. `pull` / `push` / `cleanup` / `rebase` / `squash` act on
the current repo; a trailing scope token fans `pull` / `push` / `cleanup` across `properties.yml`'s
`repos:` family in root-to-leaf `parent` order — `all` (whole family), `ai` (`ai: true`),
`dev_prd` (`default_branch: development`). `status: retired` repos are always skipped. With no
`repos:` map, a scope falls back to just this repo and says so. `<verb> --repo <name|path>` runs
one verb against another managed checkout — a family-repo name or a git checkout path (mutually
exclusive with a scope).

- **`/repo list`** — show the `repos:` map (parent tree + each repo's attributes + clone state).
- **`/repo cleanup [scope]`** — clean up a merged feature branch (switch to the default branch,
  pull, delete it), then sweep local build/cache trash and orphaned `modules/`/`tasks/`/`tests/`
  directories. Never touches `topics/`, `tmp/`, or untracked new work.
- **`/repo push [scope]`** — runs the *real* `/push` (invoke fix + invoke test + commit + push) in
  each repo. Confirm the repo list with the user first. Never skip a repo's tests; if a repo's
  tests fail, that repo is reported as failed and the run continues — surface every failure in your
  summary.
- **`/repo apply <description>`** — the two-phase Cross-Repo Change Workflow. Read
  `.ai/toolkit/instructions/repos.md` in full and follow it: apply the change on a feature branch
  in every family repo, stop at the checkpoint for the user, then ship one PR per repo.

Recognition trigger: when the user says "related repos", "the repos", "other repos", "all the
repos", "pull all repos", or similar about this vault's repo family — even without running
`/repo` — read `.ai/toolkit/instructions/repos.md` and act on it.
