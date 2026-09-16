# Common Utilities Module
Shared utilities and helper functions used across all modules in the ai_vault repository.

## Overview
This module provides common functionality that is used by other modules throughout the repository, including configuration parsing and utility functions.

## Modules
### Screenshot utilities (moved out)
The screenshot workflow lives in `modules/toolkit/screenshots/` (`configure.py`, `view.py`, `clean.py`).

### `target_repo.py` — the `--repo` target selector (CI-safe)
`resolve_target_repo(token)` maps a `--repo` / first-positional selector to a checkout path:
`None` → passthrough (nothing imported); a filesystem path → `.git`-verified, used as-is
(`properties.yml` never consulted); a bare name → fuzzy-matched against the `repos:` family (via
`backlog.common.resolve_repo`, imported lazily). `delegate(target, module_suffix, args,
caller_root=...)` re-execs the work as a fresh subprocess in the target (`cwd` + `$SIDECAR_REPO_ROOT`
per the `repo/family.py` pattern) — mandatory, because `setup.properties` caches the repo root for
the life of a process. `route_utils.peel_repo(args)` pulls `--repo`/`--repo=` out of an arg list.

### `toolchains.py` — marker-file → toolchain detection (CI-safe, stdlib only)
`detect(root)` returns the toolchain tokens a checkout has (`python`, `sdkman`, `workflows`,
`yaml`, `gradle`, `kotlin`, `agp`, …); `capabilities(root)` maps those to `<area>:<tool>` strings
(`check:libs`, `style:ruff`, `unit:pytest`, …) that `versioning.check` / `tests.style` /
`tests.unit` use to run only the sub-steps that apply.

### `utils.py`
Common utility functions for console output, error handling, and shared operations.

**Functions:**
- `success(message)` - Print success messages with ✅ emoji
- `error(message)` - Print error messages with ❌ emoji  
- `warning(message)` - Print warning messages with ⚠️ emoji
- `info(message)` - Print info messages with ℹ️ emoji

## Dependencies
This module depends on:
- `setup.properties` - For reading configuration from `properties.yml`
- Standard library: `pathlib`, `shutil`
- Internal CLI helper: `modules/toolkit/common/cli.py` (TUI-safe prompt/confirm/option handling)

## Configuration
Uses `properties.yml` at repository root:

```yaml
screenshots:
  location: "${repo_local}/screenshots"
  latest_file: "latest.png"
  preserve_files:
    - "latest.png"
  cleanup_patterns:
    - "*.png"
    - "*.jpg"
    - "*.jpeg"
```

## Architecture
The common module follows these principles:
- **Shared utilities only** - Functions used by multiple modules
- **No business logic** - Pure utility functions
- **Minimal dependencies** - Only depends on standard library and config
- **Clear error messages** - User-friendly output with emojis
- **Type hints** - Full type annotations for all functions

## Integration
Every other module imports from `common/`:

```python
from modules.common import cli
from modules.toolkit.setup.properties import get_repo_local, get_screenshots_location
from modules.toolkit.common.utils import success, error, warning, info
from modules.toolkit.common.route_utils import build_env, find_repo_root
```
