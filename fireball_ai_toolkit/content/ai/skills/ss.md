---
description: Use for viewing the latest screenshot from the centralized screenshots/ folder. Equivalent to /ss (which is /screenshots view). Also triggered by "look at my screen", "check this screenshot", or "see my screenshot".
argument-hint:
- optional context or question
hints:
- ss
- look at my screen
- check this screenshot
- see my screenshot
- look at the screenshot
instructions:
- .fireball_ai_toolkit/instructions/screenshots.md
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.screenshots.route "view"`

Then use the `view_image` tool on `screenshots/latest.png` (relative to the repository root) to view the screenshot.

Analyze the image and respond to $ARGUMENTS if provided, otherwise use the screenshot to continue helping with the current chat goal.
