---
description: "Use when editing GitHub Actions workflows or composite actions — naming, layout, the invoke-driven job pattern, action-ref pinning, and actionlint."
applyTo: ".github/workflows/**,.github/actions/**"
---
# GitHub Actions Instructions
## Layout
```
.github/
├── workflows/        # top-level workflows
└── actions/          # local composite actions, one dir per action
```

## Conventions
- **File names**: lowercase `snake_case` (`tests.yml`); composite-action dirs likewise
- **YAML**: passes `yamllint` — start with `---`; also validated by `actionlint`
- **`name:` / `run-name:`**: `name:` is a short Title Case label; `run-name:` includes the branch,
  e.g. `"Tests (${{ github.head_ref || github.ref_name }})"`
- **Triggers**: test workflows run on `pull_request` to the default branch
- **One concern per job**: a separate job per check (actionlint, pylint, pytest, ruff, yamllint, …)
  so failures are isolated in the PR checks UI

## Job Pattern
Every job is the same three steps — checkout, setup, run one invoke task:
```yaml
steps:
  - uses: actions/checkout@v7
  - uses: ./.github/actions/cicd_setup     # installs uv + .venv
  - run: |
      source .venv/bin/activate
      invoke debug.env
      invoke tests.<check>
```
The actual check logic lives in `tasks/tests/*.py`, never inline in the workflow — same
thin-wrapper rule as everywhere else (`.ai/toolkit/instructions/logic.md`).

## Action-Ref Pinning
`uses: owner/repo@vN` refs are pinned to a **major** tag (`actions/checkout@v7`). `invoke
ver.workflows` compares each ref against the latest major tag on GitHub and rewrites the pin; run
`invoke tests.actionlint` afterward. See `.ai/toolkit/instructions/versioning.md`.

## Reusable Workflow Repos
The family's shared CI lives in three **public** repos, each `main`-only with `v`-prefix dual
tags (`vX.Y.Z` + a floating `vX` force-moved by `publish_release.yml` on a `VERSION` bump):

- **`workflows_common`** — primitives everyone consumes: the `bump_version` composite action plus
  `resolve_version.yml` / `promote.yml` / `github_release.yml` / `python_tests.yml` reusables.
- **`workflows_shopify`** — the Shopify theme pipeline (`tests`/`deploy`/`release`/`dawn_sync`).
- **`workflows_web`** — the static landing-site pipeline (Vite build → S3 → CloudFront).

A consumer repo carries only thin caller workflows: `uses:
fireballenterprise/workflows_<x>/.github/workflows/<name>.yml@vN`, pinned to the floating major.
The AI/Python repos call `workflows_common/.github/workflows/python_tests.yml@v1` with a `checks`
JSON array — one matrix leg per check (`{name, invoke, node?, pre?}`), so each still shows as its
own PR check-run.

**Auth**: reusable workflows that push a branch/tag resolve the token as
`${{ steps.bot.outputs.token || github.token }}`, with the bot step gated
`if: ${{ vars.BOT_APP_ID != '' }}`. A protected repo sets `BOT_APP_ID` + `BOT_PRIVATE_KEY` → the
`fireball-actions-bot` App (ruleset bypass); an unprotected repo sets neither → `GITHUB_TOKEN`.
Callers pass `secrets: inherit`. Automated commits are authored
`Levon Becker <LevonBecker@users.noreply.github.com>` — never `github-actions[bot]`.

**Cross-repo caveat**: a reusable workflow can't `uses: ./.github/actions/…` of the *caller* (the
path resolves in the workflow repo), so `python_tests.yml` sets up `uv` inline rather than via a
`cicd_setup` composite. Edit the logic in the workflow repo + cut a new `vX.Y.Z`; a breaking
change bumps the major and every caller re-points `@vN`.

## Before Committing
`.yml` changes require `uv run --no-sync invoke fix` + `test` at 10/10 — `test` runs both
`actionlint` and `yamllint` (`.ai/toolkit/instructions/tests.md`).
