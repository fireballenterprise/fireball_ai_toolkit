---
description: "Use before building or changing any Fireball app or platform: sign-in/account, avatar and profile menu, Settings, About/splash, Help menu, brand colours, MCP, the built-in Sidecar, app lock, push, usage meters, diagnostics. Shared app code comes from fireball_kit, never from copying another app."
applyTo: "**"
---
# Fireball Kit Rule
- **A new Fireball app, or a new platform of one, starts from `invoke kit.new_app` or the
  `fireball_kit` packages.** Never copy another app's account, shell, brand, About/splash, MCP or
  built-in Sidecar code.
- **If the kit lacks something, add it to the kit first** (`fireballenterprise/fireball_kit`, local
  `../fireball_kit`), tag it, then adopt it in the app. Apps pin a kit version (a git tag).
- **An app's own copy is migration debt.** Don't spread it. Its replacement is tracked on the
  **Kit - Migration** board (org project #48, epic fireball_kit#25).
- **The shell spec is `fireball_kit/docs/app_shell.md`**, with exact labels, order and copy. In short:
  - Hosts (Mac, Windows, Linux) open to a read-only example, and any write opens the sign-in gate popup. Clients (web, iPhone/iPad, Android) are sign-in first.
  - The launch splash is the About view.
  - App screens use the **rounded-square app icon, never the round mark** (owner, 2026-10-01): About, the splash, startup and first-run screens, sign-in, the App Lock, and the taskbar, Dock and tray icons. Round marks are only for small in-window brand logos (toolbar or header).
  - Every product uses Enterprise's shared Terms and Privacy pages and `© <year> Fireball Enterprise` (no LLC outside legal documents, company_name.md).
- Until the kit covers a piece, copy **fireball_designer**'s behaviour as the reference, and file or extend the kit issue for it.
