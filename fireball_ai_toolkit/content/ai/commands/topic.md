---
name: topic
description: Switch topics, list the active topic, show the topic tree, or reindex it
argument-hint: list [all] | switch <path> | new <path> [description] | init [description] | reindex [--dry-run] | update [--dry-run]
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.topic.route "$ARGUMENTS"`


If $ARGUMENTS starts with "new", create a new topic at the given path (relative to topics/), then run init in that directory. The path may nest to any depth. Example: /topic new workshop/welding/tig [description].

If $ARGUMENTS starts with "list all", the command already prints the full topic tree (indented, active topic starred) — relay it as-is; do not rebuild it.

If $ARGUMENTS starts with "list" and does not include "all", show the active topic only and mention that "list all" reveals the full topic tree.

If $ARGUMENTS starts with "reindex", the command rebuilt topics_list.yml from the directories on disk — relay which topics it added or removed. Suggest it when a switch reports a topic "missing from the index".

After running the command, if the output shows a topic switch (contains "Switched to:"):
- The **Full path** line in the output is now the active topic root for this conversation
- ALL subsequent relative paths resolve under that full path:
  - `docs/...` → `{topic_full_path}/docs/...`
  - `2026/...` → `{topic_full_path}/2026/...`
  - Any bare filename/folder → `{topic_full_path}/...`
- Do NOT use any previously cached topic path — the new path from this output is the source of truth
- Do NOT read `active_topic.yml` to determine the path; use the command output directly
