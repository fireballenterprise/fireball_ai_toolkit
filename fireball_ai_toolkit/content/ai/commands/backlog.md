---
name: backlog
description: Track bugs / features / tasks as GitHub Issues on any repo in the family — file, list, view, work, comment, close. Use for "file a bug in X", "list the issues for X", "work on issue N", "fix all the open bugs in X".
argument-hint: add bug|feature|task --repo <name> --title "..." | list [--repo <name> | --all] | start --repo <name> --number N | close --repo <name> --number N --pr M
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.backlog.route "$ARGUMENTS"`

The two-axis type/label model, the issue body format, and the write guardrails (secret scrubbing,
batch confirmation, per-repo ship rules) live in `.ai/toolkit/instructions/backlog.md` — read it
before any `add` / `comment`. `--repo` is a fuzzy token (name, unique substring, or a word from
the repo's `purpose`); an ambiguous token makes the CLI print candidates — ask the user which,
don't guess. `list` defaults to the current repo (or `--all` for every family repo grouped by
repo); every other verb needs `--repo`. A **bare `/backlog`** with no subcommand runs
`list --all` — the whole-family open backlog.

## Recognition — what the user says maps to what to run
| user says | do |
|---|---|
| bare "backlog" / `/backlog` with nothing after it | `backlog.list --all` (the route does this automatically for the no-arg form) — the whole-family open backlog; same verbatim fencing, **client-rendered, don't rebuild or repeat it** |
| "file/log/track a bug in sidecar vscode: X", "feature request for the toolkit: Y", "add a task for chat: Z" | resolve the repo; craft a clean title + a body in the **issue format** below (ask if the report is thin). If an image was pasted, **read it and transcribe the relevant content into the body** — error text as fenced quotes, UI state as prose; note it came from a screenshot. Work out `--area` (affected module/component/topic, from the "Where it likely lives" analysis) and any `--label` nature; **confirm title + Type + area + labels with the user**, then `backlog.add --repo <t> --type <bug\|feature\|task> --title "..." --body "..." [--area <m>] [--label <nature>]` |
| "list / show the issues \| open bugs \| backlog for X", "what's left \| still open in X" | `backlog.list --repo <t>` (`--type bug` for bugs, `--label <area>` to scope to a module/topic; `--state open` by default). Output is a finished `### <repo> · <n>` heading + Markdown table, `<!--sidecar:verbatim-->`-fenced — the client renders it; **don't rebuild or repeat it** |
| "show the whole backlog", "what's open anywhere \| across the family", "any bugs open in any repo" | `backlog.list --all` (a `## … — family` heading, then one `### <repo> · <n>` + table per non-empty repo, then `*<k> other repos: none*`; `--scope ai\|dev_prd` to narrow, same `--type` / `--label` / `--mine` filters apply per repo). Same verbatim fencing — **client-rendered, don't rebuild or repeat it** |
| "work on / pick up / start / tackle issue N in X", "fix this bug" (issue in context) | `backlog.start --repo <t> --number N` then open the **target repo's** clone, branch per its ship rules (the command prints them), implement, run its `invoke fix && invoke test`, `/push` or `/pr`, then `backlog.close --repo <t> --number N --pr <n>` (or `--sha <sha>` for direct-push repos) |
| "fix all the open bugs \| issues in X", "knock out the backlog for X" | `backlog.list --repo <t> --state open --json`, **show the list, confirm the batch**, work one at a time each on its own branch/commit, `backlog.close` each, report a summary; stop and surface any that need a decision |
| "close issue N in X, fixed by PR M" | `backlog.close --repo <t> --number N --pr M` |
| "add a note to issue N", "comment on N" | `backlog.comment --repo <t> --number N --body "..."` |

For the issue body format and the guardrails every `add` / `comment` must follow, see
`.ai/toolkit/instructions/backlog.md`.
