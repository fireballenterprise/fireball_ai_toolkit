---
name: chat
description: Manage chats (start, end, list, resume)
argument-hint: start [title] | end | list | resume [pattern]
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.chat.route "$ARGUMENTS"`

If $ARGUMENTS starts with "list", render the command output as a markdown table with columns: # | Date | Title. Place the active chat (marked ⭐ active) as the last row, separated by a divider. Do not add extra commentary — just the table followed by a one-line summary (e.g. "24 chats — active: **a body on curve**").

If $ARGUMENTS is "end", before running the command you MUST update the chat file first:
1. Replace the `## Overview` placeholder with a compact summary of this session
2. Append all conversation turns under `## Chat Log` using this EXACT format (required by validator):
   ```
   **[YYYY-MM-DD HH:MM] User:** <message summary>

   **[YYYY-MM-DD HH:MM] Assistant:** <response summary>
   ```
   Use today's date and approximate times. The brackets, date, time, and role label are all required.
3. After writing the file, run the command — it validates the file then clears the active status.
Do NOT run the command first and fix the file after — write first, then run once.
