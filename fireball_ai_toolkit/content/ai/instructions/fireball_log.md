---
description: "Use whenever adding logging, diagnostics, error reporting or a Logs page to a Fireball app or host (Wrangler, Sidecar, Designer, any new app): log through the kit's FireballLog so every app shows all its logs in one place, redacted, on its own Logs page."
applyTo: "**"
---
# FireballLog Rule
- **Every Fireball app has a Logs page** (owner, 2026-10-06): users never dig through their OS for logs (Console.app, `%APPDATA%`, `~/.local/state`). The kit's viewer shows them in one place, inside the app (fireball_kit#47; spec `fireball_kit/docs/fireball_log.md`).
- **Log through FireballLog, never `print`/`console.log`/`Debug.WriteLine`** for anything a user or support might need: Swift `FireballLog`, C# `Fireball.Kit.Log`, TypeScript `@fireball/kit-web/log`. A Node host or other repo that can't import the kit mirrors the contract and pins its tests to the kit's `tests/fixtures/log/*.json`.
- **Log what happened, in plain words**, under a short Title Case source (e.g. `Agents`, `Host`, `MCP`, `Sidecar`, `App`): started/finished (with a duration), installed/updated, waiting/approved, failed (with the error's kind). Put small details in `fields`.
- **Never log content or secrets**: no prompts, chat text, MCP arguments, file contents, tokens, keys, emails or home paths. Redaction is a backstop, not a licence.
- **Levels**: `error` = something failed that the user may need to act on; `warn` = degraded or retried; `info` = normal milestones; `debug` = detail for us. Red is for errors only.
- **Reading another machine's log** (a client app showing a host's log) goes on demand over the app's own channel (e.g. Wrangler's `read_logs` relay command), never streamed to the cloud.
- **Settings has no separate log page**: logs live on the app's Logs page.
