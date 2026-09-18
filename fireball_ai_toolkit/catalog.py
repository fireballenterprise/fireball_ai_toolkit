"""Parse the canonical content tree (and a consuming repo's local overlay) into structured records.

Two content roots feed every renderer:

* ``shared`` — the packaged canonical tree (``content/`` in this repo, shipped as package data;
  mirrored into a consuming repo as ``.fireball_ai_toolkit/``)
* ``local`` — an optional per-repo overlay in the consuming repo (``.<repo>/``, e.g.
  ``.fireball_ai_vault/``)

``load_bundle()`` merges them (``local`` wins on a slug collision) and returns a
:class:`ContentBundle` the renderers consume. Nothing here writes files or knows about any
specific AI tool — that is the renderers' job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Root dir holding the canonical content in every consuming repo. Distinctively named (not the
# generic `.ai/`) so it can't collide with another tool's convention — matches the package/repo
# name.
AI_ROOT_DIRNAME = ".fireball_ai_toolkit"

# Content layers, lowest-priority first. A slug defined in a later layer overrides the earlier one.
# `shared` is the packaged canonical tree (rendered as `.fireball_ai_toolkit/`); `local` is
# the consuming repo's `.<repo>/` overlay.
LAYERS = ("shared", "local")

# Everything the toolkit ships lives under `content/`. `apply` clobber-copies each of these into
# the consuming repo verbatim; `check` drift-gates them; `contribute` maps repo edits back.
#   content/<key>/  ->  <repo path>/
CLOBBER_TREES = {
    "ai": AI_ROOT_DIRNAME,  # commands/ instructions/ skills/ — then rendered per provider dir
    "modules": "modules/fireball_ai_toolkit",  # shared Python — imported as modules.fireball_ai_toolkit.*
    "tasks": "tasks/fireball_ai_toolkit",  # shared invoke tasks
    "tests": "tests/fireball_ai_toolkit",  # tests for the shared modules
}
#   content/<key>  ->  <repo file>
CLOBBER_FILES = {
    "scripts/setup.sh": "setup.sh",
    "scripts/setup.ps1": "setup.ps1",
}

# A consuming repo may vendor only a subset of what the toolkit ships — a repo whose shared Python
# has diverged too far to clobber can still take the `.fireball_ai_toolkit/` content and
# `setup.sh` while it reconciles. `.ai-toolkit.yml` at the repo root, `vendor: [ai, scripts]`;
# absent = all of it.
#   ai      -> content/ai/      (.fireball_ai_toolkit/ + every regenerated provider file)
#   modules -> content/modules/ (modules/fireball_ai_toolkit/)
#   tasks   -> content/tasks/   (tasks/fireball_ai_toolkit/)
#   tests   -> content/tests/   (tests/fireball_ai_toolkit/)
#   scripts -> content/scripts/ (setup.sh, setup.ps1)
VENDOR_KEYS = ("ai", "modules", "tasks", "tests", "scripts")
_VENDOR_CONFIG = ".ai-toolkit.yml"


def read_vendor(repo_root: Path) -> tuple[str, ...]:
    """Which shipped trees this repo vendors, in :data:`VENDOR_KEYS` order. All of them by default."""
    cfg = repo_root / _VENDOR_CONFIG
    if not cfg.is_file():
        return VENDOR_KEYS
    data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    if "vendor" not in data:
        return VENDOR_KEYS
    picked = set(_as_list(data.get("vendor")))
    unknown = picked - set(VENDOR_KEYS)
    if unknown:
        msg = f"{_VENDOR_CONFIG}: unknown vendor keys {sorted(unknown)} (valid: {list(VENDOR_KEYS)})"
        raise ValueError(msg)
    return tuple(k for k in VENDOR_KEYS if k in picked)


def vendored_trees(repo_root: Path) -> dict[str, str]:
    """:data:`CLOBBER_TREES` filtered to what this repo vendors."""
    vendor = read_vendor(repo_root)
    return {k: v for k, v in CLOBBER_TREES.items() if k in vendor}


def vendored_files(repo_root: Path) -> dict[str, str]:
    """:data:`CLOBBER_FILES` filtered to what this repo vendors (all under the ``scripts`` key)."""
    return dict(CLOBBER_FILES) if "scripts" in read_vendor(repo_root) else {}


_EXEC_RE = re.compile(r"^!`([^`]+)`", re.MULTILINE)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _as_list(value: object) -> list[str]:
    """Normalise a frontmatter scalar/list into a list of stripped strings."""
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return ``(frontmatter_dict, body)`` for a markdown file with optional ``---`` frontmatter."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                fm = {}
            return (fm if isinstance(fm, dict) else {}), parts[2].strip()
    return {}, text.strip()


@dataclass(frozen=True)
class Command:
    """One canonical slash-command spec (``content/commands/<slug>.md``)."""

    slug: str
    description: str
    argument_hint: str
    body: str
    source: Path
    agent: str = "agent"
    allowed_tools: tuple[str, ...] = ()

    @property
    def exec_lines(self) -> list[str]:
        """Every ``!`...``` execution line in the body, in order."""
        return [match.group(1).strip() for match in _EXEC_RE.finditer(self.body)]

    @property
    def exec_line(self) -> str:
        """The first ``!`...``` execution line from the body, or ``""`` if the command has none."""
        lines = self.exec_lines
        return lines[0] if lines else ""

    @classmethod
    def from_file(cls, path: Path) -> Command:
        fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        return cls(
            slug=path.stem,
            description=str(fm.get("description", "")),
            argument_hint=str(fm.get("argument-hint", "")),
            body=body,
            source=path,
            agent=str(fm.get("agent", "agent")),
            allowed_tools=tuple(_as_list(fm.get("allowed-tools"))),
        )


@dataclass(frozen=True)
class Instruction:
    """One canonical agent-rule file (``content/instructions/<slug>.md``)."""

    slug: str
    description: str
    apply_to: str
    body: str
    source: Path
    label: str = ""

    @classmethod
    def from_file(cls, path: Path) -> Instruction:
        fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        return cls(
            slug=path.stem,
            description=str(fm.get("description", "")),
            apply_to=str(fm.get("applyTo", "")),
            body=body,
            source=path,
            label=str(fm.get("label", "")) or _derive_label(path.stem, body),
        )


def _derive_label(slug: str, body: str) -> str:
    """A human label for the AGENTS.md / copilot index: frontmatter ``label`` → body H1 → slug."""
    match = _H1_RE.search(body)
    if match:
        return re.sub(r"\s+(Instructions|Workflow)$", "", match.group(1).strip())
    return slug.replace("_", " ").replace("-", " ").title()


@dataclass(frozen=True)
class Skill:
    """One canonical skill file (``content/skills/<name>.md``).

    Flat one-file-per-skill — the ``<name>/SKILL.md`` directory shape is a *rendered* artifact
    (Claude / Copilot require it), never the canonical source.

    A canonical skill file is a **header only** — no body. ``hints`` are extra trigger phrases;
    ``instructions`` / ``commands`` are lists of repo-relative paths (``.fireball_ai_toolkit/…`` or
    ``.<repo>/…``) that the renderers expand into each provider stub's body so the agent knows
    what to read and follow when the skill fires.
    """

    name: str
    path: Path
    description: str = ""
    hints: tuple[str, ...] = ()
    instructions: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()

    @classmethod
    def from_file(cls, path: Path) -> Skill:
        fm, _ = _split_frontmatter(path.read_text(encoding="utf-8"))
        return cls(
            name=path.stem,
            path=path,
            description=str(fm.get("description", "")),
            hints=tuple(_as_list(fm.get("hints"))),
            instructions=tuple(_as_list(fm.get("instructions"))),
            commands=tuple(_as_list(fm.get("commands"))),
        )


def local_layer_name(repo_root: Path) -> str:
    """Name of the ``.<name>/`` dir holding this repo's own (non-toolkit) content — a top-level
    sibling of ``.fireball_ai_toolkit/``, never nested inside it.

    The repo's folder name (``.fireball_ai_vault/`` for a checkout named ``fireball_ai_vault``)
    when that dir exists. Falls back to the stable literal ``"local"`` when there is no local dir
    yet (must be deterministic: ``check`` renders in a temp mirror and has to match what ``apply``
    wrote).
    """
    if (repo_root / f".{repo_root.name}").is_dir():
        return repo_root.name
    return "local"


@dataclass(frozen=True)
class ContentBundle:
    """Everything the renderers need: the merged ``shared`` + ``local`` content."""

    commands: list[Command] = field(default_factory=list)
    instructions: list[Instruction] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    # slug -> layer name it was resolved from ("shared" or "local")
    origin: dict[str, str] = field(default_factory=dict)
    # the consuming repo's `.<local_name>/` dir name (e.g. "fireball_ai_vault"); "local" as a bare default
    local_name: str = "local"

    def layer_of(self, slug: str) -> str | None:
        """Which layer a slug was resolved from, or ``None`` if unknown."""
        return self.origin.get(slug)

    def is_local(self, slug: str) -> bool:
        """True when ``slug`` was resolved from the consuming repo's ``.<local_name>/`` overlay."""
        return self.origin.get(slug) == "local"


def _collect(root: Path, subdir: str, suffix: str = ".md") -> list[Path]:
    target = root / subdir
    if not target.is_dir():
        return []
    return sorted(p for p in target.glob(f"*{suffix}") if p.is_file())


def packaged_content_root() -> Path:
    """Absolute path to the ``content/`` tree bundled inside this package (all shipped trees)."""
    return (Path(__file__).resolve().parent / "content").resolve()


def packaged_ai_root() -> Path:
    """Absolute path to ``content/ai/`` — the commands/instructions/skills bundle the renderers read."""
    return packaged_content_root() / "ai"


def load_bundle(
    *,
    canonical_root: Path | None = None,
    local_root: Path | None = None,
    local_name: str = "local",
) -> ContentBundle:
    """Merge the content layers into a :class:`ContentBundle`.

    Layers apply lowest-priority first: ``canonical_root`` (``shared``, defaults to the packaged
    tree) → ``local_root`` (``local``). A slug present in a later layer replaces the earlier one;
    :attr:`ContentBundle.origin` records which layer won.

    Args:
        canonical_root: the ``ai/`` bundle root (``content/ai/`` packaged, ``.fireball_ai_toolkit/`` in a
            consuming repo). Defaults to the packaged ``content/ai/``.
        local_root: consuming repo's ``.<local_name>/`` root. Optional.
        local_name: the local dir's name, recorded on the bundle for the renderers' pointers.
    """
    layers: list[tuple[str, Path]] = [("shared", (canonical_root or packaged_ai_root()).resolve())]
    if local_root is not None:
        layers.append(("local", local_root.resolve()))

    commands: dict[str, Command] = {}
    instructions: dict[str, Instruction] = {}
    skills: dict[str, Skill] = {}
    origin: dict[str, str] = {}

    for layer_name, root in layers:
        if not root.is_dir():
            continue
        for path in _collect(root, "commands"):
            commands[path.stem] = Command.from_file(path)
            origin[path.stem] = layer_name
        for path in _collect(root, "instructions"):
            instructions[path.stem] = Instruction.from_file(path)
            origin[path.stem] = layer_name
        for path in _collect(root, "skills"):
            skills[path.stem] = Skill.from_file(path)
            origin[path.stem] = layer_name

    return ContentBundle(
        commands=[commands[k] for k in sorted(commands)],
        instructions=[instructions[k] for k in sorted(instructions)],
        skills=[skills[k] for k in sorted(skills)],
        origin=origin,
        local_name=local_name,
    )
