# Topic Module
Topic workspace management behind the `topic.*` invoke tasks and the `/topic` slash command.
Every file exposes a `main()` entry point, runnable standalone via `python -m modules.toolkit.topic.<name>`.
See `.ai/toolkit/instructions/topics.md` for the design this module implements.

## Files
- `active.py` — get/set/clear the currently active topic, tracked in `active_topic.yml` at the
  repo root (gitignored)
- `update_list.py` — get/add/check/sync entries in `topics/topics_list.yml` (`topics:` index + the
  optional `topic_meta:` map of `path -> {description, instructions}`); flattens a legacy
  `topics_layout:` nested tree to `topics:` on read so a repo that pulls this tooling keeps working
  with no manual step
- `templates.py` — generates the thin-pointer `AGENTS.md`/`CLAUDE.md` content written into each
  topic directory, including the `## Instructions` section built from `topic_meta.instructions`
- `init.py` — scaffold `chats/`, `plans/`, `docs/`, and instruction files for the topic in the
  current directory, and register it (with any `--description`/`--instructions`) in
  `topics_list.yml`; also exposes `scaffold()`/`split_instructions()`, shared with `new.py`
  (`topic.init` / `/topic init`)
- `new.py` — create a new topic directory at `topics/<path>` (nesting to any depth; missing
  parents created) and initialize it via `init.scaffold()` (`topic.new` / `/topic new`)
- `reindex.py` — rebuild `topics_list.yml` from the topic directories on disk (any dir under
  `topics/` holding an `AGENTS.md`): register every one, drop entries whose directory is gone,
  leave `topic_meta:` for survivors alone; `--dry-run` reports without writing
  (`topic.reindex` / `/topic reindex`)
- `switch.py` — auto-save any chat active in the outgoing topic, validate the target topic exists
  (self-heal the index when `topics/<path>/` exists but isn't registered; fuzzy-match suggestions
  when the directory is genuinely absent), update `active_topic.yml`, surface the new topic's
  `AGENTS.md` and any resumable active chat (`topic.switch` / `/topic switch`, or bare `/topic <path>`)
- `list.py` — show the active topic, or the whole topic tree (`--all`) rendered as an indented
  tree with the active topic starred (`topic.list` / `/topic list`)
- `update.py` — regenerate topic `AGENTS.md`/`CLAUDE.md` from `templates.py` + `topic_meta`; scope
  with `--current-only` or `--topic=a,b` (regeneration is wholesale — see the instruction file's
  caveat) (`topic.update` / `/topic update`)
- `route.py` — routes `/topic <subcommand> ...` arguments to the module above matching that
  subcommand (`init`, `list`, `new`, `reindex`, `switch`, `update`), defaulting to `switch` when
  the first token isn't a known subcommand (the bare `/topic <path>` shorthand)
- `README.md` — this file

## Conventions
- Resolve the repo root via `modules.toolkit.setup.properties.get_repo_root()`
- Report outcomes via `modules.common.utils` (`success`/`error`/`info`)
- Topic paths are `/`-joined and nest to **any depth** (`workshop/welding/tig`). The index
  (`topics_list.yml` `topics:`) stores the flat path list; `templates.py`, `list.py`'s tree
  view, and every path join handle depth transparently — there is no depth cap
