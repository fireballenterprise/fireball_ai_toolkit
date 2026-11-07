---
description: "Use whenever setting or touching an app's minimum OS: Xcode project.yml deploymentTarget, Package.swift platforms, Sparkle minimumSystemVersion, Android minSdk, .NET SupportedOSPlatformVersion / Windows TFMs, .deb Depends floors, store listings and download pages' Requires lines. Every Fireball app officially supports the current OS version and the last one."
applyTo: "**"
---
# Minimum OS Versions Rule
- **Every Fireball app officially supports the current OS version and the last one, on every platform** (owner, 2026-11-07; replaces "current plus two back"). Only those two are tested and claimed:

  | Platform | Supported (tested) | Floor | Where it's set |
  |---|---|---|---|
  | macOS | **26 and 27** | **26** (hard) | project.yml `deploymentTarget.macOS: "26.0"`, `Package.swift` `.macOS(.v26)`, Sparkle `LSMinimumSystemVersion` |
  | iOS / iPadOS | **26 and 27** | **26** (hard) | project.yml `deploymentTarget.iOS: "26.0"`, `Package.swift` `.iOS(.v26)` |
  | watchOS | **26 and 27** | **26** (hard) | project.yml / `Package.swift` `.watchOS(.v26)` |
  | Android | **17 and 16** | 15 (API 35) | `minSdk = 35`; `targetSdk` = the current release |
  | Windows | **11 and 10** | 10 (2004+, 10.0.19041) | `SupportedOSPlatformVersion` / `net*-windows10.0.19041.0` |
  | Ubuntu | **26.04 and 24.04 LTS** | 24.04 | the .deb `Depends` floors (libc6 and friends) |

- **Apple is hard-floored at 26.** Note the numbering: Apple went from 18 straight to 26, so iOS 18 / macOS 15 / watchOS 11 are not "one or two back"; never target them.
- **Android, Windows and Ubuntu keep the floors above**: an older version may work, but it is not tested or promised. Store listings and download pages name the two supported versions.
- **fireball_kit holds the Apple floor.** Its `Package.swift` platforms set the minimum, and an app can't go below the kit it links, so change the kit first.
- **No availability checks for the floor's APIs.** The 26 APIs (Liquid Glass and friends) need no `#available`; only APIs new in the current version (27) go behind `#available(macOS 27, iOS 27, *)` / `Build.VERSION.SDK_INT` / `OperatingSystem.IsWindowsVersionAtLeast`. Never raise a floor just to use one API.
- **Older devices keep their last supported release.** App stores and Sparkle stop offering updates below the floor; keep the old downloads up.
- **Each autumn, when new OS versions ship, move every row up by one** so it stays "current and last". Update this table in the same change.
- When you touch a project still below a floor, raise it in that change, or file an issue on the app's board if it needs its own release.
