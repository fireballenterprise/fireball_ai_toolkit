---
name: ss
description: View the latest screenshot from the centralized screenshots folder
argument-hint: [optional context or question]
agent: agent
---

!`uv run --no-sync python -m modules.toolkit.screenshots.route "view"`

Then use the `view_image` tool on `screenshots/latest.png` (relative to the repository root) to view the screenshot.

Analyze the image and respond to $ARGUMENTS if provided, otherwise use the screenshot to continue helping with the current chat goal.
