---
description: "Use when working with screenshots or the shared screenshots/ folder — where they go, the /ss viewing workflow, and the /screenshots command."
applyTo: "screenshots/**,modules/toolkit/screenshots/**"
---
# Screenshots Instructions
Rules for the `screenshots/` folder at the repository root.

## Purpose
`screenshots/` is the **single shared folder for all screenshots across the entire repository** —
every topic uses it, there are no topic-specific screenshot folders. Git LFS tracks `*.png`,
`*.jpg`, `*.svg`.

## Rules
- **NEVER create a `screenshots/` subfolder inside a topic directory** — always the repo-root folder
- `latest.png` is a scratch file — the most recently copied screenshot, for an AI tool to read
- Reference screenshots by repo-root-relative path (`screenshots/latest.png`), never absolute

## Commands
| Command | What it does |
|---|---|
| `/screenshots view` (alias `/ss`) | Copies the latest macOS screenshot to `screenshots/latest.png` for AI viewing |
| `/screenshots configure` | Points macOS screenshot capture at the `screenshots/` folder |
| `/screenshots clean` | Deletes accumulated screenshot images from `screenshots/` (keeps `latest.png`); also runs before `/push` |

## Viewing a Screenshot
When the user shares a screenshot or asks you to look at one:
1. The user runs `/ss` (= `/screenshots view`) to copy the latest to `screenshots/latest.png`
2. Use `view_image` on `screenshots/latest.png`
3. Treat the image as context for the current conversation — don't auto-create a doc unless asked

## Implementation
`modules/toolkit/screenshots/` (`configure.py`, `view.py`, `clean.py`, `route.py`) — see its `README.md`.
Path resolution via `modules/toolkit/setup/properties.py`.
