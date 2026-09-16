---
description: "Use when working with the properties.yml version/latest_changes keys that drive change logs, or the generated docs/change_logs/ entries."
applyTo: "properties.yml,modules/toolkit/docs/**,docs/change_logs/**"
---
# Change Log Standards
Per-entry markdown change logs at `docs/change_logs/<category>/<name>.md`, generated from
`properties.yml` — not hand-written prose. One file per entry, newest version at the top.
`modules/toolkit/docs/lib/change_logs.py`'s `CHANGELOG_CATEGORIES` tuple is empty by default. Add a
category (e.g. `cloudformation` for CDK stacks, keyed by construct_id) to that tuple once there's
an entry worth logging; everything else in the module already supports it.

## Source of Truth
**`properties.yml`, not the markdown file** — each category section has one entry per name:

```yaml
<category>:
  <name>:
    version: 1.0.0
    latest_changes:
      author: Ada Lovelace    # git config user.name — modules.toolkit.setup.properties.get_git_author()
      date: 2026-08-11
      description: Initial Release    # comma-separate for multiple bullets: "Added X, Fixed Y"
```

Bumped by hand when the entry changes meaningfully — not automated. **A brand-new entry's first
`description` is always `"Initial Release"`.**

## Rendered Entry Format
From `modules/toolkit/docs/lib/change_logs.py`'s `expected_entry_text()`:

```markdown
## 1.0.0 - 2026-08-11 - Ada Lovelace
* Initial Release
```

`## <version> - <date> - <author>` heading, one `* ` bullet per comma-separated `description`
item, blank line, next-newest entry below. No H1 title — the first line is always a `##` entry
heading.

## Sync Mechanism
`modules/toolkit/docs/lib/change_logs.py`:
- `check_each_log(update=True)` — prepends any missing entry (idempotent; a current entry is a
  no-op). Backs `invoke docs.update-changelogs`, which also runs as part of `invoke fix`
- `check_each_log(update=False)` — read-only; raises `ValueError` on the first stale entry instead
  of writing. Backs the drift gate `tests/drift/docs/test_changelogs_current.py`. A no-op while
  `CHANGELOG_CATEGORIES` is empty.
