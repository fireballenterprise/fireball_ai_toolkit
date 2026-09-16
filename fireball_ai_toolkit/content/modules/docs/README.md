# Docs Module
Changelog sync — keeps `docs/change_logs/<category>/<name>.md` in sync with `properties.yml`.

## Commands
```sh
uv run --no-sync invoke docs.update-changelogs
```

## What It Does
Each root `properties.yml` key listed in `lib/change_logs.py`'s `CHANGELOG_CATEGORIES` tuple owns
a change log per entry under `docs/change_logs/<category>/<name>.md`. `CHANGELOG_CATEGORIES` is
empty for now — nothing here is version-tracked in that shape yet, so both the sync task and its
drift-test counterpart (`tests/toolkit/drift/docs/test_changelogs_current.py`) are no-ops until a category
is added. See `.github/instructions/changelogs.instructions.md` for the full `properties.yml` entry
shape and rendered markdown format.

## Files
- `update.py` — `main()`, the entry point called by `tasks/ai/docs.py`
- `lib/change_logs.py` — the actual sync logic (`check_each_log`, used both by
  `invoke docs.update-changelogs` with `update=True` and the drift test with `update=False`)
- `README.md` — this file
