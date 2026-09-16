"""Detect which toolchains a checkout uses, from its marker files.

``versioning.check`` / ``tests.style`` / ``tests.unit`` call :func:`detect` (or the
capability helpers below) to decide which sub-checks / linters / test runners actually apply to a
repo — so pointing any of them at another repo (``--repo``) Just Works: a Kotlin app runs the
Gradle checks and skips the Python ones, a Python library does the reverse, nobody has to
cherry-pick per repo.

**CI-safe**: stdlib only. No ``properties`` import, no network, no shelling out.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["capabilities", "detect", "enables", "has_agp"]

#: Directory names never walked when sniffing for source files.
_PRUNE = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "build",
        ".gradle",
        ".idea",
        "tmp",
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        ".kotlin",
        "dist",
        ".mypy_cache",
    }
)

#: toolchain token → the capability strings it turns on. A capability is ``<area>:<name>`` where
#: area is ``check`` (versioning.check), ``style`` (tests.style) or ``unit`` (tests.unit).
_ENABLES: dict[str, set[str]] = {
    "python": {"check:python", "check:libs", "style:ruff", "style:pylint", "unit:pytest"},
    "sdkman": {"check:sdkman"},
    "workflows": {"check:workflows", "style:actionlint"},
    "yaml": {"style:yamllint"},
    "kotlin": {"style:ktlint", "style:detekt", "unit:gradle"},
    "agp": {"style:android-lint"},
}


def _iter_sources(root: Path, suffixes: tuple[str, ...], *, limit: int = 5000) -> bool:
    """True as soon as a file with one of ``suffixes`` is found anywhere under ``root`` (pruned)."""
    seen = 0
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in _PRUNE:
                    stack.append(entry)
                continue
            seen += 1
            if entry.suffix in suffixes:
                return True
            if seen >= limit:
                return False
    return False


def _has_yaml(root: Path) -> bool:
    """Any YAML outside ``.github/workflows`` (which is the ``workflows`` toolchain, not ``yaml``)."""
    for pattern in ("*.yml", "*.yaml"):
        if any(root.glob(pattern)):
            return True
        for sub in (".github", ".sidecar", "config", ".ai"):
            if any((root / sub).rglob(pattern)):
                return True
    return False


def _has_workflows(root: Path) -> bool:
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        return False
    return any(p.stat().st_size > 0 for p in wf.iterdir() if p.suffix in (".yml", ".yaml"))


def _sdkman_candidates(root: Path) -> set[str]:
    """The candidate names pinned in ``.sdkmanrc`` (``java``, ``gradle``, ``kotlin``, …)."""
    path = root / ".sdkmanrc"
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            out.add(stripped.split("=", 1)[0].strip())
    return out


def has_agp(root: Path) -> bool:
    """True when the Android Gradle Plugin is referenced (so ``./gradlew lint`` is meaningful)."""
    for name in ("gradle/libs.versions.toml", "build.gradle.kts", "build.gradle", "app/build.gradle.kts"):
        candidate = root / name
        if candidate.is_file() and "com.android." in candidate.read_text(encoding="utf-8", errors="ignore"):
            return True
    return False


def detect(root: Path) -> set[str]:
    """The set of toolchain tokens present in ``root``."""
    tokens: set[str] = set()

    if (root / "pyproject.toml").is_file() or (root / "uv.lock").is_file():
        tokens.add("python")

    tokens |= _sdkman_candidates(root)
    if tokens & {"java", "gradle", "kotlin"} or (root / ".sdkmanrc").is_file():
        tokens.add("sdkman")

    if _has_workflows(root):
        tokens.add("workflows")
    if _has_yaml(root):
        tokens.add("yaml")

    gradle_markers = ("settings.gradle", "settings.gradle.kts", "build.gradle", "build.gradle.kts")
    if any((root / marker).is_file() for marker in gradle_markers):
        tokens.add("gradle")
        # `.kt` only — `.gradle.kts` build scripts are Gradle config, not Kotlin app source.
        if _iter_sources(root, (".kt",)):
            tokens.add("kotlin")
        if has_agp(root):
            tokens.add("agp")

    if (root / "package.json").is_file():
        tokens.add("node")
    if (root / "Gemfile").is_file():
        tokens.add("ruby")

    return tokens


def enables(token: str) -> set[str]:
    """Capability strings a single toolchain token turns on."""
    return set(_ENABLES.get(token, set()))


def capabilities(root: Path) -> set[str]:
    """Union of :func:`enables` over every toolchain :func:`detect`ed in ``root``."""
    caps: set[str] = set()
    for token in detect(root):
        caps |= enables(token)
    return caps
