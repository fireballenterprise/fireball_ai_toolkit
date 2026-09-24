# modules/fireball_ai_toolkit/repo/
Repository-level git and PR operations, plus repo-**family** fan-out. Thin CLI wrappers — logic
lives in these modules, reached via `/repo`, the dedicated aliases, or `inv repo.*`.

## Commands
| Command | Module | Purpose |
|---|---|---|
| `/repo` (no args) | `route.py` | print usage |
| `/repo list` | `family.py` | show the `repos:` / `lineage:` family map + which clones exist locally |
| `/repo push` (`/push`) `[all]` | `push.py` / `family.py` | pull → detect changes → commit with timestamp → push → rsync content to iCloud. `all` runs the full `/push` (fix + test + commit + push) in every family repo. |
| `/repo pull` (`/pull`) `[all]` | `pull.py` / `family.py` | stash → `pull --rebase` → restore stash; also pulls iCloud. `all` switches each family repo to its verified default branch and `pull --ff-only`s. |
| `/repo cleanup` (`/cleanup`) `[all]` | `cleanup.py` / `family.py` | after merge: switch to the default branch, pull, delete the merged local branch; sweep local build/cache trash + orphaned dirs; `git rm` redundant `.gitkeep` placeholders (staged, not committed). `all` = same, per family repo. |
| `/repo apply <desc>` | — | agent-driven two-phase Cross-Repo Change Workflow (see `repos.md` instructions) |
| `/rebase` | `rebase.py` | rebase the current branch onto the remote default branch (optional squash first) |
| `/squash` | `squash.py` | anchored squash of all commits to the root commit, optional force push |
| `/pr` `/pr-notes` | `pr_diff.py`, `pr_notes.py`, `pr_create.py` | draft PR notes (Summary + Changes) for the current branch and open the PR via `gh` |
| `/ship-it` | `pr_push.py` + `pr_create.py` | push the branch and open the PR in one step |

`route.py` dispatches the `/repo` subcommands; a trailing `all` token on `pull` / `push` /
`cleanup` routes to `family.py`, which resolves `properties.yml`'s `repos:` + `repos_local:` and
iterates in root-to-leaf lineage order. With no `repos:` map, `all` falls back to the single repo.
Branch naming and PR format: see `.github/instructions/git.instructions.md`.

## iCloud Sync
`push.py` / `pull.py` rsync repo **content** (topics, screenshots, docs) to the iCloud Obsidian
vault when `icloud.enabled: true` in `properties.yml` — excluding `.git`, `.claude`, and other
hidden files so the mobile vault stays small (~700KB). It's off by default.

## Notes
- Every module has a `main()` entry point and uses `modules/fireball_ai_toolkit/setup/properties.py` for path resolution
- The screenshot workflow moved to `modules/fireball_ai_toolkit/screenshots/`
