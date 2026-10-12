---
description: "Use before building or changing any Fireball app or platform: sign-in/account, avatar and profile menu, sidebar, title bar, Settings, About/splash, Help menu, banners and states, brand colors, MCP, the built-in Sidecar, app lock, push, usage meters, logs, local files, updates. Shared app code comes from fireball_kit, never from copying another app."
applyTo: "**"
---
# Fireball Kit Rule
- **A new Fireball app, or a new platform of one, starts from `invoke kit.new_app` and the `fireball_kit`
  packages** (`fireballenterprise/fireball_kit`, local `../fireball_kit`). Never copy another app's account, shell,
  brand, About/splash, MCP or built-in Sidecar code.
- **Pin a kit tag** (current: **0.5.0**): Swift `kitTag` with `exact:` in `Package.swift`; C# the
  `external/fireball_kit` submodule at the tag; web/API `"@fireball/kit-web": "github:fireballenterprise/fireball_kit#<tag>"`;
  Android `fireballKitTag` + `includeBuild` in `settings.gradle.kts`. Test an unreleased kit with `FIREBALL_KIT_PATH`.
- **If the kit lacks something, add it to the kit first,** tag it, then adopt it. An app's own copy is migration debt.
- **Specs:** `fireball_kit/docs/app_shell.md` (exact labels, order, copy) and `docs/settings_layout.md`. Full inventory and
  decisions: orchestrator `.fireball_orchestrator/instructions/kit.md`; UI rules: `ui.md`.

## What to use, where
| Need | Swift (Mac, iPhone, iPad) | C# (Windows, Linux) | Web / API (`@fireball/kit-web`) | Android (Kotlin) |
|---|---|---|---|---|
| Sign-in, account, seats | `FireballAccount` | `Fireball.Kit.Account` | `./signin`; API `./server/*` | `account` |
| Gate, first run | `FireballShellRootView`, sign-in gate | `SignInGate`, `ExampleBanner` | `./app-shell` | `FireballClientGate` |
| Title bar | `FireballTitleBarCluster` (MCP · Sidecar · avatar), `FireballSidebarToggle` | `FireballTitleBar` (icon, File Edit View Window Help, cluster) | `./app-shell` header | top app bar |
| Profile menu | `FireballProfileMenuButton`, `FireballAvatar` | `ShellMenuViews.ProfileFlyout` | `./profile-menu` | `FireballProfileDropdown` |
| Sidebar, rail, drawer | `FireballSidebarSplit`, `FireballDrawer` | `FireballSidebar` | `./app-shell` nav | (not in kit yet) |
| Sidecar button + panel | `FireballSidecarButton`, `FireballSidecarPanel` | `SidecarButton`, `SidecarPanel` | `./sidecar-button` | `FireballSidecarButton` |
| Banners and states | `FireballBanner`, `FireballDeviceLimitSheet`, `FireballLockedFeatureView`, `FireballNotAnsweringCard`, `.fireballDevBadge` | `ShellBanner`, `NotAnsweringCard`, `DevBadge` | `createShellBanner`, `createDevBadge` | (not in kit yet) |
| About, splash, menus | `FireballAboutView` / `Panel` / `Sheet`, `FireballShellCommands` | `AboutWindow`, `ShellMenus` | `aboutLinks` | `FireballAboutContent` |
| Settings, Help | `FireballSettings*`, `FireballHelpTree` | `SettingsFrame`, `HelpTree` | `./settings` | `FireballSettings*` |
| MCP | `FireballMCP`, `FireballMCPStatusPill` | `Fireball.Kit.MCP` | | |
| Brand tokens | `FireballBrand` | `FireballTokens` | `fireball-tokens.css` | `FireballTokens` |
| Logs, paths | `FireballLog`, `FireballPaths` (`~/.fireball_<app>`) | `Kit.Log`, `Kit.Paths` | `./log`, `./paths` | |
| Updates, What's New | `FireballUpdater`, `FireballWhatsNew` | `Kit.Updater` | | Play Store |
| App lock, push, usage | `FireballAppLock`, `FireballPush`, `FireballUsage` | | API `./server/push` | `applock` |

## Musts
- One sidebar (home alone on top, A→Z sections, Settings gear bottom-left with the version), one small sidebar icon in the
  header, **no page name in the header**. Trailing cluster: MCP pill (only while MCP runs) · Sidecar button · avatar.
- Profile menu: Name · Email │ Account │ About · Help │ Settings… │ Sign Out. Nothing else.
- One neutral banner at a time; a hint of red only. Hosts (Mac, Windows, Linux) open to a read-only example; clients (web,
  iPhone/iPad, Android) are sign-in first. The launch splash is the About view, with the rounded-square app icon.
- Every UI action is an MCP tool; sign-in survives rebuilds; run `FireballShellConformance` in the app's tests.
- Every product uses Enterprise's shared Terms and Privacy pages and `© <year> Fireball Enterprise`.
