---
name: screenshots
description: Screenshot workflow (configure macOS capture location, view latest, clean up)
argument-hint: configure | view | clean
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.screenshots.route "$ARGUMENTS"`

- `configure` — point macOS screenshot capture at the repo's `screenshots/` folder
- `view` — copy the latest screenshot to `screenshots/latest.png` (also `/ss`), then view it
- `clean` — delete accumulated screenshot images (keeps `latest.png`)

After `view`, use the `view_image` tool on `screenshots/latest.png` (relative to the repo root) and
respond to $ARGUMENTS if provided.
