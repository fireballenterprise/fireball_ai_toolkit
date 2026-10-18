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
import warnings
from dataclasses import dataclass, field, replace
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
    "ai": AI_ROOT_DIRNAME,  # instructions/ skills/ — then rendered per provider dir
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
    """One canonical skill — the unit behind a slash command *and* an AI-loadable capability.

    Two source forms, one skill:

    * **flat** — ``skills/<name>.md`` (frontmatter + the full slash-command text as the body)
    * **bundle** — ``skills/<name>/SKILL.md`` (same frontmatter/body) plus any resource files next
      to it (scripts, examples, templates). Having both ``<name>.md`` and ``<name>/`` is an error.

    Frontmatter: ``description``, ``argument-hint``, ``hints`` (extra trigger phrases),
    ``instructions`` (repo-relative rule/skill paths the renderers list as "read and follow"), and
    the two switches ``user-invocable`` / ``ai-invocable`` (both default true; ``ai-invocable:
    false`` renders as ``disable-model-invocation: true``). ``allowed-tools`` is optional.
    """

    name: str  # normalised ([a-z0-9-]+) — the generated skill name, folder and slash name
    path: Path
    description: str = ""
    argument_hint: str = ""
    body: str = ""
    hints: tuple[str, ...] = ()
    instructions: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    user_invocable: bool = True
    ai_invocable: bool = True
    # bundle form only: resource files next to SKILL.md, relative to the bundle dir, sorted
    resources: tuple[Path, ...] = ()
    bundle_dir: Path | None = None
    # the name as authored (file/folder stem) when it differed from the normalised ``name``
    source_name: str = ""

    @property
    def exec_lines(self) -> list[str]:
        """Every ``!`...``` execution line in the body, in order."""
        return [match.group(1).strip() for match in _EXEC_RE.finditer(self.body)]

    @property
    def exec_line(self) -> str:
        """The first ``!`...``` execution line from the body, or ``""`` if the skill has none."""
        lines = self.exec_lines
        return lines[0] if lines else ""

    @classmethod
    def from_file(cls, path: Path, *, name: str | None = None, bundle_dir: Path | None = None) -> Skill:
        fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        resources: tuple[Path, ...] = ()
        if bundle_dir is not None:
            resources = tuple(
                sorted(
                    p.relative_to(bundle_dir)
                    for p in bundle_dir.rglob("*")
                    if p.is_file()
                    and p != path
                    and not any(part.startswith(".") for part in p.relative_to(bundle_dir).parts)
                    and "__pycache__" not in p.parts
                )
            )
        source = name or path.stem
        norm = _normalized(source, path)
        hints = _as_list(fm.get("hints"))
        if source != norm and source not in hints:
            hints.append(source)  # typing the original spelling must keep matching
        return cls(
            name=norm,
            source_name=source if source != norm else "",
            path=path,
            description=str(fm.get("description", "")),
            argument_hint=str(fm.get("argument-hint", "")),
            body=body,
            hints=tuple(hints),
            instructions=tuple(_as_list(fm.get("instructions"))),
            allowed_tools=tuple(_as_list(fm.get("allowed-tools"))),
            user_invocable=_as_bool(fm.get("user-invocable"), default=True),
            ai_invocable=_as_bool(fm.get("ai-invocable"), default=True),
            resources=resources,
            bundle_dir=bundle_dir,
        )


SKILL_NAME_MAX = 64
SKILL_DESCRIPTION_MAX = 1024
SKILL_NAME_RE = re.compile(r"[a-z0-9-]+")


def normalize_skill_name(name: str) -> str:
    """The generated skill name/folder: lowercase, every run of characters outside ``[a-z0-9]``
    (``_`` included) becomes one ``-``, leading/trailing ``-`` stripped, at most 64 chars.

    Copilot's Agent Skills runtime silently drops a skill whose name is not ``[a-z0-9-]+`` or does
    not equal its folder, so the generated name is always normalised (``add_bug`` -> ``add-bug``).
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:SKILL_NAME_MAX].strip("-")


SIDECAR_SKILL_NAME_RE = re.compile(r"[a-z0-9_]+")


def sidecar_skill_name(name: str) -> str:
    """The Sidecar file stem for a skill: lowercase, every run of characters outside ``[a-z0-9]``
    becomes one ``_`` (``add-bug`` / ``add_bug`` / ``Add Bug`` -> ``add_bug``), edges stripped."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _normalized(name: str, source: Path) -> str:
    norm = normalize_skill_name(name)
    if not norm:
        msg = f"skill {name!r} ({source}) has no usable characters — a skill name needs at least one of [a-z0-9]"
        raise ValueError(msg)
    return norm


def _as_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "no", "0", "off")
    return bool(value)


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


def _collect_skills(root: Path) -> list[Skill]:
    """Every skill under ``<root>/skills/`` — flat ``<name>.md`` or bundle ``<name>/SKILL.md``."""
    target = root / "skills"
    if not target.is_dir():
        return []
    found: dict[str, Skill] = {}
    for path in sorted(target.iterdir()):
        if path.name.startswith("."):
            continue
        if path.is_file() and path.suffix == ".md":
            skill = Skill.from_file(path)
        elif path.is_dir() and (path / "SKILL.md").is_file():
            skill = Skill.from_file(path / "SKILL.md", name=path.name, bundle_dir=path)
        else:
            continue
        name = skill.name
        if name in found:
            other = found[name]
            if (other.source_name or other.name) == (skill.source_name or skill.name):
                msg = f"skill {name!r} is defined twice in {target}: both {name}.md and {name}/ exist — keep one"
            else:
                msg = (
                    f"skills {other.path.relative_to(target)} and {path.relative_to(target)} in {target} both "
                    f"normalise to the generated skill name {name!r} — rename or remove one"
                )
            raise ValueError(msg)
        found[name] = skill
    return [found[k] for k in sorted(found)]


def _legacy_commands(root: Path) -> dict[str, Skill]:
    """Read a leftover ``commands/`` dir (toolkit < 2.0) as skills, with a deprecation warning."""
    paths = _collect(root, "commands")
    if not paths:
        return {}
    warnings.warn(
        f"{root / 'commands'}: the commands/ directory is deprecated and will stop being read in the next "
        "release — merge each command body into the same-named skills/<slug>.md (toolkit 2.0.0).",
        DeprecationWarning,
        stacklevel=3,
    )
    out: dict[str, Skill] = {}
    for path in paths:
        fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        norm = _normalized(path.stem, path)
        out[norm] = Skill(
            name=norm,
            source_name=path.stem if path.stem != norm else "",
            path=path,
            description=str(fm.get("description", "")),
            argument_hint=str(fm.get("argument-hint", "")),
            body=body,
            allowed_tools=tuple(_as_list(fm.get("allowed-tools"))),
        )
    return out


def _with_legacy(skill: Skill, command: Skill | None) -> Skill:
    """A same-layer legacy command supplies the body/hint a header-only (old-style) skill lacks."""
    if command is None or skill.body:
        return skill
    return replace(
        skill,
        body=command.body,
        argument_hint=skill.argument_hint or command.argument_hint,
        allowed_tools=skill.allowed_tools or command.allowed_tools,
        description=skill.description or command.description,
    )


def packaged_content_root() -> Path:
    """Absolute path to the ``content/`` tree bundled inside this package (all shipped trees)."""
    return (Path(__file__).resolve().parent / "content").resolve()


def packaged_ai_root() -> Path:
    """Absolute path to ``content/ai/`` — the instructions/skills bundle the renderers read."""
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

    instructions: dict[str, Instruction] = {}
    skills: dict[str, Skill] = {}
    origin: dict[str, str] = {}

    for layer_name, root in layers:
        if not root.is_dir():
            continue
        for path in _collect(root, "instructions"):
            instructions[path.stem] = Instruction.from_file(path)
            origin[path.stem] = layer_name
        # Legacy `commands/` (toolkit < 2.0): read tolerantly for one release, skills win.
        legacy = _legacy_commands(root)
        for skill in _collect_skills(root):
            skills[skill.name] = _with_legacy(skill, legacy.pop(skill.name, None))
            origin[skill.name] = layer_name
        for slug, command in legacy.items():
            skills[slug] = command
            origin[slug] = layer_name

    return ContentBundle(
        instructions=[instructions[k] for k in sorted(instructions)],
        skills=[skills[k] for k in sorted(skills)],
        origin=origin,
        local_name=local_name,
    )
