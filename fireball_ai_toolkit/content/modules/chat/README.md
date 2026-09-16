# Chat Module
Dated planning-chat logging behind the `chat.*` invoke tasks and the `/chat` slash command. Every
file exposes a `main()` entry point, runnable standalone via `python -m modules.toolkit.chat.<name>`. See
`.ai/toolkit/instructions/topics.md` for the design this module implements.

## Files
- `active.py` — get/set/clear the active chat tracker (`active.yml`) inside a given topic
  directory (gitignored)
- `start.py` — resolve the active topic, auto-close any chat already active there, build a
  `YYYYMMDD_slug.md` filename, write the templated chat file (`## Overview`/`## Chat Log`
  placeholders), and mark it active (`chat.start` / `/chat start`)
- `end.py` — two entry points: `auto_close()` (used internally by `start.py`'s auto-end and
  `topic.switch`'s auto-save — commits whatever exists, no validation) and `main()` (the real
  `/chat end` — refuses to close while `## Overview` still has placeholder text or `## Chat Log`
  has no real `**[YYYY-MM-DD HH:MM] User/Assistant:**` entries, then clears the tracker **without
  committing**) (`chat.end` / `/chat end`)
- `list.py` — show every chat file in the active topic, starring the active one
  (`chat.list` / `/chat list`)
- `resume.py` — reopen an existing chat by filename/title substring match, asking for a more
  specific pattern if ambiguous (`chat.resume` / `/chat resume`)
- `route.py` — routes `/chat <subcommand> ...` arguments to the module above matching that
  subcommand (`start`, `end`, `list`, `resume`) — no bare-arg shorthand, since a bare string is
  ambiguous between a new title and a resume pattern
- `README.md` — this file

## Conventions
- Resolve the repo root via `modules.toolkit.setup.properties.get_repo_root()`
- Report outcomes via `modules.common.utils` (`success`/`error`)
- The chat file's actual content — the real `## Overview` summary and `## Chat Log` entries — is
  written by the calling agent via its own Edit tool before running `/chat end`, not by this
  module; `end.py` only validates and clears state
