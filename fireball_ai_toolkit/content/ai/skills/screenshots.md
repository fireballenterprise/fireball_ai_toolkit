---
description: Use for the screenshot workflow — configure the macOS capture location, view the latest screenshot, or clean up accumulated images. Equivalent to /screenshots (view is also /ss).
argument-hint: configure | view | clean
hints:
- screenshots
instructions:
- .fireball_ai_toolkit/instructions/screenshots.md
- .fireball_ai_toolkit/skills/ss.md
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.screenshots.route "$ARGUMENTS"`

- `configure` — point macOS screenshot capture at the repo's `screenshots/` folder
- `view` — copy the latest screenshot to `screenshots/latest.png` (also `/ss`), then view it
- `clean` — delete accumulated screenshot images (keeps `latest.png`)

After `view`, use the `view_image` tool on `screenshots/latest.png` (relative to the repo root) and
respond to $ARGUMENTS if provided.
