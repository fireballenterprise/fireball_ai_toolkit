"""``migrate_skills`` — fold a consuming repo's own ``.<repo>/commands/`` into ``.<repo>/skills/``.

Toolkit 2.0.0 made skills the slash commands: ``skills/<slug>.md`` holds the full command text,
and ``commands/`` is gone. The toolkit's own content is migrated in this repo; this module does the
same for a repo's *local* layer (``.fireball_orchestrator/``, ``.fireball_ai_vault/``, ``.ai_vault/``…).

For every ``commands/<slug>.md`` it writes ``skills/<slug>.md`` with:

* the command's full body,
* ``description`` from the existing skill header (else the command), ``argument-hint`` from the command,
  ``hints`` / ``instructions`` carried over from the skill (a ``commands:`` entry that pointed at
  another command becomes an ``instructions:`` entry on that skill; the self entry is dropped),
* no ``name`` / ``agent`` keys, and no ``user-invocable`` / ``ai-invocable`` (omitted = both true).

Then it deletes the local ``commands/`` dir and rewrites ``.<repo>/commands/…`` /
``.fireball_ai_toolkit/commands/…`` path references in the local instructions and skills to
``skills/``. Anything else that still mentions commands or prompts (``.github/prompts``,
``.claude/commands``, globs) is **reported, not rewritten**. Idempotent: with no ``commands/`` dir
there is nothing to do. ``dry_run`` reports without writing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .catalog import _as_list, _split_frontmatter, local_layer_name

_UNSAFE = re.compile(r"(?<![\w.])commands/|\.github/prompts|\.prompt\.md|\.claude/commands|\.sidecar/commands")


@dataclass
class MigrationReport:
    dry_run: bool = False
    merged: list[str] = field(default_factory=list)  # skills written (merged or created)
    skipped: list[str] = field(default_factory=list)  # commands left alone, with the reason
    rewritten: list[str] = field(default_factory=list)  # docs whose references were rewritten
    manual: list[str] = field(default_factory=list)  # "<file>:<line>: <text>" left for a human
    removed_commands_dir: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.merged or self.rewritten or self.removed_commands_dir)

    def lines(self) -> list[str]:
        tag = "[dry-run] would " if self.dry_run else ""
        out = [f"{tag}merge into skills: {', '.join(self.merged) or 'nothing'}"]
        out += [f"skipped: {item}" for item in self.skipped]
        out += [f"{tag}rewrite references in: {item}" for item in self.rewritten]
        if self.removed_commands_dir:
            out.append(f"{tag}delete the local commands/ directory")
        if self.manual:
            out.append("NOT rewritten (review by hand):")
            out += [f"  {item}" for item in self.manual]
        return out


def _dump(fm: dict, body: str) -> str:
    head = yaml.safe_dump(fm, sort_keys=False, width=10000, allow_unicode=True, default_flow_style=False)
    return f"---\n{head}---\n" + (f"\n{body.strip()}\n" if body.strip() else "")


def _merge(slug: str, command: Path, skill: Path, local_name: str) -> str:
    cfm, body = _split_frontmatter(command.read_text(encoding="utf-8"))
    sfm, _ = _split_frontmatter(skill.read_text(encoding="utf-8")) if skill.is_file() else ({}, "")
    fm: dict[str, object] = {"description": sfm.get("description") or cfm.get("description", "")}
    if cfm.get("argument-hint"):
        fm["argument-hint"] = cfm["argument-hint"]
    if sfm.get("hints"):
        fm["hints"] = _as_list(sfm["hints"])
    instructions = _as_list(sfm.get("instructions"))
    for ref in _as_list(sfm.get("commands")):
        match = re.search(r"commands/([\w-]+)\.md$", ref)
        if match and match.group(1) != slug:
            instructions.append(re.sub(r"/commands/", "/skills/", ref))
    if instructions:
        fm["instructions"] = instructions
    for key, value in cfm.items():
        if key not in ("name", "description", "argument-hint", "agent"):
            fm[key] = value
    for key in ("user-invocable", "ai-invocable"):
        if key in sfm:
            fm[key] = sfm[key]
    return _dump(fm, body)


def migrate_skills(repo_root: Path, *, dry_run: bool = False) -> MigrationReport:
    """Merge ``.<repo>/commands/`` into ``.<repo>/skills/`` for ``repo_root``. See module docs."""
    repo_root = repo_root.resolve()
    report = MigrationReport(dry_run=dry_run)
    local_name = local_layer_name(repo_root)
    local = repo_root / f".{local_name}"
    commands_dir = local / "commands"
    if not commands_dir.is_dir():
        return report

    skills_dir = local / "skills"
    leftover = False
    for command in sorted(commands_dir.glob("*.md")):
        slug = command.stem
        skill = skills_dir / f"{slug}.md"
        if skill.is_file() and _split_frontmatter(skill.read_text(encoding="utf-8"))[1].strip():
            report.skipped.append(f"{slug}: skills/{slug}.md already has a body — merge by hand, command kept")
            leftover = True
            continue
        report.merged.append(slug)
        if not dry_run:
            skills_dir.mkdir(parents=True, exist_ok=True)
            skill.write_text(_merge(slug, command, skill, local_name), encoding="utf-8")
            command.unlink()
    # Old-style header-only skills that had no command of their own stay as they are (they keep a body-less header).
    if not leftover:
        report.removed_commands_dir = True
        if not dry_run:
            for stray in commands_dir.rglob("*"):
                if stray.is_file():
                    stray.unlink()
            for d in sorted((p for p in commands_dir.rglob("*") if p.is_dir()), reverse=True):
                d.rmdir()
            commands_dir.rmdir()

    _rewrite_references(local, local_name, report, dry_run=dry_run)
    return report


def _rewrite_references(local: Path, local_name: str, report: MigrationReport, *, dry_run: bool) -> None:
    pattern = re.compile(rf"(\.(?:fireball_ai_toolkit|{re.escape(local_name)}))/commands/")
    targets = sorted([*(local / "instructions").glob("*.md"), *(local / "skills").glob("*.md")])
    for path in targets:
        text = path.read_text(encoding="utf-8")
        new = pattern.sub(r"\1/skills/", text)
        if new != text:
            report.rewritten.append(str(path.relative_to(local.parent)))
            if not dry_run:
                path.write_text(new, encoding="utf-8")
        for number, line in enumerate(new.splitlines(), 1):
            if _UNSAFE.search(line):
                report.manual.append(f"{path.relative_to(local.parent)}:{number}: {line.strip()[:120]}")
