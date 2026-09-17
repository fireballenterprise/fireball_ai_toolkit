"""Check a repo's `.sdkmanrc` toolchain pins (JDK / Gradle / Kotlin / …) against SDKMAN's own
`sdk list`, and — on apply — rewrite `.sdkmanrc` (and the Gradle wrapper) to the newest usable id.

Only meaningful in a repo that ships a `.sdkmanrc` (today just `fireball_sidecar_android`). When
there's no `.sdkmanrc` this exits 3 — the same "nothing to do" convention `libs`/`python` use —
so `ver.update`'s check loop can call it unconditionally.

SDKMAN has no version-range syntax: `.sdkmanrc` pins an exact identifier per candidate
(`java=26.0.2-tem`, `gradle=9.7.0`), which is why this exists — the pins otherwise only move by
hand. `sdk list <candidate>` is the source of truth for what's installable; its output format is
not a stable contract, so the parsing here is deliberately loose (pull version-shaped tokens out
of whatever grid/table it prints) rather than column-precise.

Known-bad identifiers are skipped: a `# sdkman-skip: <candidate> <id> [<id> …]` comment line in
`.sdkmanrc` adds to `_DEFAULT_SKIP` below. Seeded with `gradle 9.7.1` — that distribution is
corrupt when fetched through SDKMAN (the install reports the package as corrupt); stay on `9.7.0`,
resume at `9.7.2+`.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..common import cli
from ..common.utils import info, success, warning
from ..setup.properties import get_repo_local

# Identifiers `sdk list` may offer that must never be picked automatically.
_DEFAULT_SKIP: dict[str, set[str]] = {
    "gradle": {"9.7.1"},
}

# A token is a pre-release / early-access build we don't auto-adopt.
_PRERELEASE = re.compile(r"(?:-rc-?\d*|-m\d+|-beta\d*|-alpha\d*|-ea|\+ea|-b\d+|-snapshot)", re.IGNORECASE)

# A SDKMAN identifier: a dotted version, an optional `+build`, an optional `-vendor`/channel suffix.
_IDENTIFIER = re.compile(r"\b(\d+(?:\.\d+){1,3})(\+[\w.]+)?(-[a-z][\w.-]*)?\b", re.IGNORECASE)


def read_sdkmanrc(repo_path: Path) -> dict[str, str]:
    """Parse `.sdkmanrc` into `{candidate: identifier}`. Missing file → empty dict."""
    path = repo_path / ".sdkmanrc"
    if not path.exists():
        return {}
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        pins[key.strip()] = value.strip()
    return pins


def read_skip_list(repo_path: Path) -> dict[str, set[str]]:
    """`_DEFAULT_SKIP` plus any `# sdkman-skip: <candidate> <id> …` lines from `.sdkmanrc`."""
    skip = {candidate: set(ids) for candidate, ids in _DEFAULT_SKIP.items()}
    path = repo_path / ".sdkmanrc"
    if not path.exists():
        return skip
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"#\s*sdkman-skip:\s*(\S+)\s+(.+)", line.strip())
        if match:
            candidate, ids = match.group(1), match.group(2).split()
            skip.setdefault(candidate, set()).update(ids)
    return skip


def _version_key(identifier: str) -> tuple[int, ...]:
    """Ordering key from an identifier's leading dotted version (`26.0.2-tem` → `(26, 0, 2)`)."""
    match = re.match(r"(\d+(?:\.\d+)*)", identifier)
    return tuple(int(part) for part in match.group(1).split(".")) if match else (0,)


def _channel_suffix(identifier: str) -> str:
    """The `-vendor` channel a java id carries (`26.0.2-tem` → `-tem`), or `` for plain semver ids."""
    match = re.search(r"(-[a-z][\w]*)$", identifier, re.IGNORECASE)
    return match.group(1).lower() if match else ""


def available_identifiers(candidate: str) -> list[str]:
    """Every version-shaped identifier `sdk list <candidate>` offers. Empty on any failure."""
    try:
        result = subprocess.run(
            ["bash", "-lc", f'source "$HOME/.sdkman/bin/sdkman-init.sh" && sdk list {candidate}'],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError:
        return []
    found: list[str] = []
    for line in result.stdout.splitlines():
        for match in _IDENTIFIER.finditer(line):
            found.append("".join(part for part in match.groups() if part))
    return found


def latest_identifier(candidate: str, current: str, skip: set[str]) -> str | None:
    """Newest installable identifier for `candidate` that shares `current`'s channel, isn't a
    pre-release, isn't skipped, and sorts above `current`. `None` when already current / unknown."""
    want_suffix = _channel_suffix(current)
    current_key = _version_key(current)
    best: str | None = None
    best_key: tuple[int, ...] = current_key
    for identifier in available_identifiers(candidate):
        if identifier in skip or _PRERELEASE.search(identifier):
            continue
        if _channel_suffix(identifier) != want_suffix:
            continue
        key = _version_key(identifier)
        if key > best_key:
            best, best_key = identifier, key
    return best


def _wrapper_properties(repo_path: Path) -> Path:
    return repo_path / "gradle" / "wrapper" / "gradle-wrapper.properties"


def bump_gradle_wrapper(repo_path: Path, version: str) -> bool:
    """Point `gradle-wrapper.properties`' `distributionUrl` at `version`. Returns True if changed."""
    path = _wrapper_properties(repo_path)
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    updated = re.sub(
        r"(distributionUrl=.*gradle-)\d+(?:\.\d+){1,3}(-(?:bin|all)\.zip)",
        rf"\g<1>{version}\g<2>",
        text,
    )
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _write_sdkmanrc(repo_path: Path, updates: dict[str, str]) -> None:
    path = repo_path / ".sdkmanrc"
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in updates:
            lines[index] = f"{key}={updates[key]}"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@cli.command()
@cli.option("--dry-run", is_flag=True, help="Show updates without applying")
@cli.option("--yes", "-y", "no_confirm", is_flag=True, help="Skip confirmation")
def main(dry_run: bool, no_confirm: bool) -> None:
    """Check `.sdkmanrc` toolchain pins against SDKMAN and rewrite them to the newest usable id.

    This updates the pins only. `sdk env install` (actually installing the JDK / Gradle / …) is the
    `/upgrade` step. No `.sdkmanrc` → nothing to do.
    """
    info("Checking .sdkmanrc toolchain versions...")
    repo_path = get_repo_local()
    pins = read_sdkmanrc(repo_path)
    if not pins:
        success("No .sdkmanrc in this repo — nothing to check")
        raise SystemExit(3)

    skip_list = read_skip_list(repo_path)
    updates: dict[str, str] = {}
    cli.echo("\n📊 SDKMAN Toolchain Status:")
    for candidate, current in pins.items():
        latest = latest_identifier(candidate, current, skip_list.get(candidate, set()))
        if latest:
            updates[candidate] = latest
            cli.echo(f"   {candidate:<10} {current}  →  {latest}")
        else:
            cli.echo(f"   {candidate:<10} {current}  (current)")

    if not updates:
        cli.echo()
        success("All .sdkmanrc toolchain pins are current")
        raise SystemExit(3)

    wrapper_target = updates.get("gradle")
    if wrapper_target and _wrapper_properties(repo_path).exists():
        cli.echo(f"   {'wrapper':<10} gradle-wrapper.properties  →  {wrapper_target}")

    if dry_run:
        cli.echo("\n🔍 Dry-run mode: No changes made")
        return

    if not no_confirm:
        cli.echo()
        summary = ", ".join(f"{c} {v}" for c, v in updates.items())
        if not cli.confirm(f"💡 Update .sdkmanrc to {summary}?"):
            cli.echo("Cancelled.")
            raise SystemExit(2)

    _write_sdkmanrc(repo_path, updates)
    cli.echo("\n✏️  Updated .sdkmanrc")
    if wrapper_target and bump_gradle_wrapper(repo_path, wrapper_target):
        cli.echo("✏️  Updated gradle/wrapper/gradle-wrapper.properties")
    else:
        warning("Gradle wrapper not updated — run `./gradlew wrapper --gradle-version <v>` if it drifts")
    cli.echo("\n💡 Run /upgrade to install the new toolchain (sdk env install)")
    cli.echo()


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
