---
name: pr
description: Draft PR notes for the current feature branch and open a Pull Request via gh (does not push).
argument-hint: no arguments required
agent: agent
---

If this repo is `pull_request: false` in `properties.yml` (`/repo self`), it ships by direct push,
not PRs — `pr_create` will refuse. Tell the user to use `/ship-it` (or push the default branch)
instead.

Gather the branch and diff context:

!`uv run --no-sync python -m modules.toolkit.repo.route "pr_diff"`

If that fails, show the full output to the user and ask how they'd like to proceed.

Using the branch, commit log, and diff above, write a Pull Request description (same as `/pr-notes`,
but do NOT save it to a file this time — just hold it in context):
- `## Summary` — 1-3 sentences describing the overall change
- `## Changes` — a bulleted list of the key changes (one bullet per logical change, not per file)

## Find or file a tracking issue
Before creating the PR, look for the issue this work closes:
1. List this repo's open issues: `uv run --no-sync python -m modules.toolkit.backlog.route "list --state open --json"`
2. Compare each issue's title against the branch name, commit log, and diff above.
   - **One clear match** (branch name / commits / diff obviously point at that issue) — use it,
     no need to ask.
   - **Several plausible matches, or none** — show the candidates as `#N — title` and ask the
     user which this PR tracks. Offer: pick one, file a new issue now for tracking (ask type +
     confirm title/body per `.ai/toolkit/instructions/backlog.md`, then
     `uv run --no-sync python -m modules.toolkit.backlog.route "add <bug|feature|task> --title \"...\" --body \"...\" --label \"In Progress\""`
     — label it `In Progress` right away since a PR is being opened for it in this same breath,
     unlike a normal backlog filing — and note the returned issue number), or skip linking.
3. Carry the resolved issue number (if any) into the PR create step below as `--issue <N>`.

## Create the pull request
1. Note the `Base branch:` value printed above.
2. Draft a concise PR title (under 70 characters) summarizing the change.
3. Run (add `--issue=<N>` only if a tracking issue was resolved above):
   `uv run --no-sync python -m modules.toolkit.repo.route "pr_create --title=\"<title>\" --content=\"<notes>\" --issue=<N>"`
4. Report the PR URL to the user, and which issue it's tracking (if any).

`pr_create` appends a `Tracks #<N>` line to the PR body (GitHub cross-references it on the issue
automatically) and posts a `PR: <url>` comment on the issue — both directions link without further
action. This is a soft link, not an auto-close; `/backlog close --pr <N>` still does the final
"Fixed in #<pr>" + close once the fix has shipped.

If a PR already exists for this branch, `pr_create` reports its URL instead of erroring (still
linking `--issue` if one was resolved) — just relay that to the user.
