---
description: "Use whenever adding or changing an MCP server or MCP tools in a Fireball native app (Designer, Wrangler, any new app): every MCP tool call must show in the app's MCP status ticker with a short '<Area> - <Mode> - <Tool>' label, so the user always sees what the AI is doing."
applyTo: "**"
---
# MCP Status Ticker Rule
- **Every Fireball app with a native MCP server shows the MCP status ticker** (owner, 2026-10-06): the kit's MCP pill (`FireballMCPStatusPill`, fireball_kit#43) lights up and grows to show what the AI client is doing, so it's never just "the AI is controlling my app".
- **Each MCP tool gets a label**: 2–3 short parts, `<Area> - <Mode> - <Tool>`, joined with " - ". Examples:
  - **Designer:** `<Workspace> - <Mode> - <Tool>`, like "3D - Solid - Extrude", "3D - Drawing - Line", "Library - Load Project".
  - **Wrangler:** `<Area> - <Section> - <Action>`, like "Settings - Import - Setup", "Settings - Account - Add", "Agents - Create".
- **Where the labels live:** one mapping table next to the app's MCP tool catalog, a humanised fallback for an unmapped tool, and a test that every MCP tool has a label. A new MCP tool isn't done until it has its label.
- **What goes in a label:** never arguments, file paths, prompts, tokens or other secrets; the label says what kind of step it is, not its data.
- **How to report a call:** the app calls `ticker.begin(label:client:)` / `ticker.end(token, error:)` around every MCP tool call it serves. A failed call shows in the warn tone. Leave the pacing (≥ 0.8 s per label, short queue, history on hover) to the kit; don't reimplement it.
- **Apps without an MCP server** (e.g. Sidecar today) don't need it. Add it the day they get one.
