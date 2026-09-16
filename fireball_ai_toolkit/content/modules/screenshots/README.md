# modules/toolkit/screenshots/
The screenshot workflow — one shared `screenshots/` folder at the repo root serves every topic
(see `.github/instructions/screenshots.instructions.md`).

| File | Subcommand | Purpose |
|---|---|---|
| `configure.py` | `/screenshots configure` | Point macOS screenshot capture at `screenshots/` (`defaults write com.apple.screencapture location`) |
| `view.py` | `/screenshots view` (also `/ss`) | Copy the newest screenshot to `screenshots/latest.png` for an AI tool to read |
| `clean.py` | `/screenshots clean` | Delete accumulated screenshot images (keeps `latest.png`); also run automatically before `/push` |
| `route.py` | — | Dispatches `configure` / `view` / `clean` to the modules above |

Invoke tasks: `inv screenshots.configure` / `inv screenshots.view` / `inv screenshots.clean`.

Path resolution goes through `modules/toolkit/setup/properties.py` (`get_screenshots_location()`,
`get_screenshots_latest_file()`).
