---
description: "Use whenever setting or touching an app's minimum OS: Xcode project.yml deploymentTarget, Package.swift platforms, Sparkle minimumSystemVersion, Android minSdk, .NET SupportedOSPlatformVersion / Windows TFMs, .deb Depends floors, store listings and download pages' Requires lines. Every Fireball app supports the current OS plus two versions back."
applyTo: "**"
---
# Minimum OS Versions Rule
- **Every Fireball app has the same floors: the current OS plus two versions back** (owner, 2026-10-05):

  | Platform | Minimum (as of 2026-10) | Where it's set |
  |---|---|---|
  | macOS | **15** | project.yml `deploymentTarget.macOS`, `Package.swift` `.macOS(.v15)`, Sparkle `LSMinimumSystemVersion` |
  | iOS / iPadOS | **18** | project.yml `deploymentTarget.iOS`, `Package.swift` `.iOS(.v18)` |
  | watchOS | **11** | project.yml / `Package.swift` |
  | Android | **15** (API 35) | `minSdk = 35`; `targetSdk` = the current release |
  | Windows | **10 (2004+, 10.0.19041) and 11** | `SupportedOSPlatformVersion` / `net*-windows10.0.19041.0` |
  | Ubuntu | **24.04 LTS** and newer | the .deb `Depends` floors (libc6 and friends) |

- **fireball_kit holds the Apple floor.** Its `Package.swift` platforms set the minimum, and an app can't go below the kit it links, so change the kit first.
- **Newer-OS features go behind availability checks** (`#available(macOS 26, *)`, `Build.VERSION.SDK_INT`, `OperatingSystem.IsWindowsVersionAtLeast`). Never raise a floor just to use one API.
- **Older devices keep their last supported release.** App stores and Sparkle stop offering updates below the floor; keep the old downloads up.
- **Each autumn, when new OS versions ship, raise every floor by one** so it stays "current plus two back". Update this table in the same change.
- When you touch a project still below a floor, raise it in that change, or file an issue on the app's board if it needs its own release.
