# modules/backlog
Track bugs / features / tasks as **GitHub Issues**, one tracker per family repo, driven by `gh`.
No local state. Reachable as `/backlog` (+ the `/add_bug`, `/add_feature`, `/add_task` aliases)
and `invoke backlog.*`.

| file | what |
|---|---|
| `route.py` | `/backlog <sub> ...` argument dispatch (dispatch only) |
| `add.py` | `backlog.add` — open an issue (native Type + area/nature labels) |
| `list.py` | `backlog.list` — list a repo's issues (defaults to this repo) |
| `view.py` | `backlog.view` — show one issue |
| `start.py` | `backlog.start` — show + self-assign an issue, print the repo's ship rules |
| `comment.py` | `backlog.comment` — add a comment |
| `close.py` | `backlog.close` — close, optionally noting the PR / sha that fixed it |
| `common.py` | repo resolution (`resolve_repo`), `gh` wrappers, issue creation, secret scrub, image upload |

## Classification — Type + labels
Two independent axes:

- **Issue Type** (org-native `Bug` / `Feature` / `Task`) — set from `--type`. The only thing the
  tool classifies automatically. A repo whose org has no issue types is filed without a Type (a
  warning is printed).
- **Labels** — never a `bug`-next-to-Type-`Bug` mirror. They carry:
  - **area**: *where* the issue is. Every issue gets its repo's area label (`fireball_sidecar_vscode`
    → `Sidecar VSCode`); `--area "backlog,verbs"` adds finer ones — the affected **module,
    component, topic, or concept** when known (`backlog`, `router`, `topics`, `size_charts`,
    `verbs`, `labels`, …).
  - **nature**: *what kind* — `--label "Regression,Usage Failure,UI"` (also `Hallucination`,
    `Performance`, `Docs`, `Refactor`, `New Module`, …). Free-form; whatever helps triage.

Any label that doesn't exist yet is created on the fly (`label_color()` picks a stable colour by
name; an already-present label keeps its own colour/description). Filter with
`backlog list --type bug` (native Type search) and `backlog list --label backlog` (any label).

## Repo targeting
`--repo` takes a fuzzy token resolved against `properties.yml` `repos:` — exact name, unique name
substring, or best word overlap against the repo's `purpose`. Ambiguous → the CLI prints the
candidates and exits so the skill can ask. `list` defaults to the current repo; every other verb
needs `--repo` (issues live on a sibling).

## Images
GitHub has no issue-attachment API. The **skill** transcribes a pasted screenshot into the issue
text. For a real on-disk file, `--images "a.png b.png"` uploads each to a per-repo `issue-assets`
pseudo-release and embeds the stable URL.
