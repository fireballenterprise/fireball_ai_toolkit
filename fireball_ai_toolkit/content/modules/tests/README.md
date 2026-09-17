# Tests Module — lint / format / unit running
Toolchain-aware lint, format, and unit-test running for the toolkit and every repo it manages.
The invoke tasks (`tests.style`, `tests.unit`, and the bare `fix` / `test` aggregates) are thin
wrappers — all the discovery and per-tool logic lives here.

## Usage
```sh
uv run --no-sync invoke tests.style                 # every applicable linter / formatter
uv run --no-sync invoke tests.style --fix           # + apply autofixes (ruff, ktlint)
uv run --no-sync invoke tests.style ruff            # just one
uv run --no-sync invoke tests.style --repo ../app   # lint another checkout
uv run --no-sync invoke tests.unit                  # every applicable unit-test runner
uv run --no-sync invoke tests.unit --scope versioning   # pytest marker subset
```

## How it works
`style.py` / `unit.py` ask `common.toolchains.capabilities(repo_root)` which tools apply, then run
each. A Python repo → ruff + pylint + yamllint + actionlint + pytest; a Kotlin/Gradle repo →
ktlint + detekt + android-lint + gradle-unit. Naming one (`tests.style ktlint`) forces just that
one even if the toolchain isn't detected.

A tool that isn't installed (`shutil.which` miss, or a Gradle task that doesn't exist) is reported
**skipped** — it never fails `invoke test`. Only a tool that reported real offences fails it.

## Files
- `common.py` — `ToolResult` (`ok` / `offenses` / `skipped`), `run()`, `gradlew()`, `summarise()`
- `style.py` — `tests.style` entry: discover + run linters / formatters
- `unit.py` — `tests.unit` entry: discover + run unit-test runners
- one module per tool — `applies(root) -> bool`, `check(root) -> ToolResult`, optional `fix(root)`:
  `ruff`, `pylint`, `yamllint`, `actionlint` (Python / YAML / Actions); `ktlint`, `detekt`,
  `android_lint` (Kotlin, via `./gradlew`); `pytest`, `gradle_unit` (unit suites)

The `fireball_ai_toolkit` drift gate and `mdfix` stay in `tasks/main.py` — they only resolve
where the `fireball_ai_toolkit` package is installed.
