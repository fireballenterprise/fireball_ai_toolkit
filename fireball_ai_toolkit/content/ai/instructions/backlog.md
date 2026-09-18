---
description: "Use when filing, triaging, working, or closing a backlog item (bug / feature / task) as a GitHub Issue on any repo in the family — the two-axis type/label model, the issue body format, and the write guardrails."
---
# Backlog Instructions
The backlog is GitHub Issues — there is no local bug/backlog markdown. `/backlog` (and the
`/add_bug`, `/add_feature`, `/add_task` aliases) file and drive them; `invoke backlog.*` is the
CRUD layer. This file is the tool-neutral "how" — see `.fireball_ai_toolkit/commands/backlog.md` for the
verb-to-CLI mapping.

## Type vs. labels — two axes, never conflate
- **Type** (`--type bug|feature|task`) is the org-native GitHub **issue Type**. That is the whole
  bug/feature/task classification — there is no `bug` label.
- **Labels** carry *area* and *nature*:
  - *area* — every issue automatically gets its repo's area (`AI Toolkit`, `Sidecar VSCode`,
    …). Add finer `--area` values when known: the affected **module, component, topic, or
    concept** (`--area backlog`, `--area router`, `--area topics`), or "where it surfaces" when
    that differs from the repo the fix lands in.
  - *nature* — `--label`: `Regression`, `Usage Failure`, `UI`, `Hallucination`, `Performance`,
    `Docs`. Any missing label is created automatically.
- **Propose the `--area` / `--label` values at the confirm step** — never file without showing
  them.

## `--repo` resolution
Fuzzy token — a name, a unique substring, or a word from the repo's `purpose`. An ambiguous token
makes the CLI print candidates: ask the user which, don't guess. `list` defaults to the current
repo; every other verb needs `--repo`. A **bare `/backlog`** (no subcommand at all) is routed to
`list --all` — `list` with any argument still defaults to the current repo.

## Reading `list` output
`list` already prints finished Markdown — a `### <repo> · <count>` heading and a `# / Title /
Labels` table (issue numbers linked, titles truncated, the repo's own area label dropped from the
Labels cell) — fenced in `<!--sidecar:verbatim-->` markers. The Sidecar chat client renders that
block itself; if you ever do see it in a result, **relay it as-is — do not rebuild it into prose or
a bullet list, and do not repeat a block the client has already shown.** A bare `/backlog list`
lists **this** repo — say which repo the heading names and offer `--repo <name>` for another. An
empty result prints `*No <state> issues in <repo>.*` and is a real answer, not a failure — pass it
through rather than reporting the exit code.

`list --all` aggregates every active family repo: a `## <State> issues — family` heading, a
`**<total> ... across <N> repos**` line, then one `### <repo> · <count>` + table section per repo
with issues, and a trailing `*<k> other repos: none*` for the empty ones (or `*No <state> issues
in any family repo.*` when everything is empty). Use it for "the whole backlog" / "what's open
anywhere"; narrow with `--scope ai|dev_prd`. The per-repo `--type` / `--label` / `--state` /
`--mine` / `--limit` filters still apply. `--all` and `--repo` are mutually exclusive. Same
`<!--sidecar:verbatim-->` fencing — the client renders it; never rebuild or repeat it. This is
also what a bare `/backlog` resolves to.

## Issue body format
Written for an AI to pick up and work — err verbose, but lead with a human summary:

```
**Summary:** 1-2 lines a human skims to know what this is.

## What happens
<full repro: the report verbatim where it helps; transcribed screenshot content; repro steps>

## Where it likely lives
<repo/file/function pointers, suspected cause — only if known; omit rather than guess>

## Done when
<concrete acceptance: the behaviour that proves it's fixed; the smoke check to run>
```

Feature / task variant: `**Summary:**` then `## Request` then `## Why / details` then
`## Done when`.

If an image was pasted, **read it and transcribe the relevant content into the body** — error
text as fenced quotes, UI state as prose; note it came from a screenshot.

## Guardrails
- **Scrub secrets / PII before every `add` and `comment`** — API keys, tokens, passwords, `.env`
  values, AWS account IDs + ARNs, Cognito IDs, connection strings, creds-in-URLs, customer
  emails. The CLI runs a backstop pass; you do the primary, context-aware one. Matters most for
  transcribed screenshots and pasted logs — transcribe the *error*, not the secret. If redacting
  would gut the repro, ask the user how to proceed rather than posting it.
- **Confirm any multi-issue batch** before starting; work one issue at a time, each on its own
  branch/commit.
- **Honour each repo's `properties.yml` ship rules** — `backlog.start` prints them.
  `pull_request: true` → feature branch + PR (assigned to the user). `pull_request: false` →
  commit straight to the default branch, no PR. Never open a PR or push to a shared branch
  without naming the repo and branch first.
- Never merge a PR yourself.

## Linking a PR to its issue
`/pr` and `/ship-it` look for the issue a PR is fixing/implementing before creating it (see
`.fireball_ai_toolkit/commands/pr.md`) — matching against the branch/commits/diff, asking the user when it's
unclear, and offering to file a new issue on the spot for tracking. `pr_create --issue <N>` then
soft-links the two: a `Tracks #<N>` line in the PR body plus a `PR: <url>` comment on the issue,
both directions, no auto-close. That's separate from `backlog.close --pr <N>`, which is the actual
"Fixed in #<pr>" + close once the fix has shipped.

An issue **filed by that flow** (rather than found already open) gets the `In Progress` nature
label at creation — a PR is being opened for it in the same breath, so unlike a normal backlog
filing it's never in the plain "not started yet" state. A normal `/backlog add` never adds this
label on its own.
