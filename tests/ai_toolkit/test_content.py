"""Parsing the canonical content trees and a local overlay."""

import ast
from pathlib import Path

import pytest

from fireball_ai_toolkit.catalog import load_bundle, packaged_ai_root, packaged_content_root

pytestmark = pytest.mark.ai_toolkit


def test_packaged_bundle_parses():
    bundle = load_bundle(canonical_root=packaged_ai_root())
    assert bundle.skills, "expected canonical skills"
    assert bundle.instructions, "expected canonical instructions"
    assert all(s.name and s.description for s in bundle.skills)
    assert all(origin == "shared" for origin in bundle.origin.values())


def test_commands_dir_is_gone():
    assert not (packaged_ai_root() / "commands").exists()


def test_every_skill_carries_its_full_text():
    """A skill IS the slash command: every canonical skill has a body (the command text)."""
    bundle = load_bundle(canonical_root=packaged_ai_root())
    assert all(s.body.strip() for s in bundle.skills), [s.name for s in bundle.skills if not s.body.strip()]


def test_skill_instruction_paths_resolve():
    """Every path in a canonical skill's `instructions:` list is a real file."""
    ai_root = packaged_ai_root()
    bundle = load_bundle(canonical_root=ai_root)
    missing = []
    for skill in bundle.skills:
        for path in skill.instructions:
            rel = path.removeprefix(".fireball_ai_toolkit/")
            if not (ai_root / rel).is_file():
                missing.append(f"{skill.name}: {path}")
    assert not missing, "skill paths that do not resolve:\n" + "\n".join(missing)


def test_no_content_points_at_the_removed_commands_dir():
    offenders = [
        str(p.relative_to(packaged_ai_root()))
        for p in packaged_ai_root().rglob("*.md")
        if ".fireball_ai_toolkit/commands/" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders


def test_skill_exec_line_extracted():
    bundle = load_bundle(canonical_root=packaged_ai_root())
    push = next((s for s in bundle.skills if s.name == "push"), None)
    assert push is not None
    assert push.exec_line.startswith("uv run")


def test_switches_default_true_and_parse(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "a.md").write_text("---\ndescription: d\n---\nbody\n")
    (skills / "b.md").write_text("---\ndescription: d\nuser-invocable: false\nai-invocable: false\n---\nbody\n")
    by = {s.name: s for s in load_bundle(canonical_root=tmp_path).skills}
    assert (by["a"].user_invocable, by["a"].ai_invocable) == (True, True)
    assert (by["b"].user_invocable, by["b"].ai_invocable) == (False, False)


def test_skill_bundle_form_loads_with_resources(tmp_path):
    skills = tmp_path / "skills"
    (skills / "big" / "scripts").mkdir(parents=True)
    (skills / "big" / "SKILL.md").write_text("---\ndescription: big\n---\nbody\n")
    (skills / "big" / "scripts" / "run.sh").write_text("echo hi\n")
    (skills / "big" / "notes.txt").write_text("n\n")
    (skills / "big" / ".hidden").write_text("x\n")
    big = load_bundle(canonical_root=tmp_path).skills[0]
    assert big.name == "big"
    assert big.body == "body"
    assert big.resources == (Path("notes.txt"), Path("scripts/run.sh"))


def test_skill_defined_in_both_forms_is_an_error(tmp_path):
    skills = tmp_path / "skills"
    (skills / "x").mkdir(parents=True)
    (skills / "x" / "SKILL.md").write_text("---\ndescription: d\n---\nb\n")
    (skills / "x.md").write_text("---\ndescription: d\n---\nb\n")
    with pytest.raises(ValueError, match="both x.md and x/"):
        load_bundle(canonical_root=tmp_path)


def test_legacy_commands_dir_is_read_with_a_deprecation_warning(tmp_path):
    (tmp_path / "commands").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "commands" / "push.md").write_text("---\ndescription: cmd\nargument-hint: x\n---\ncommand body\n")
    (tmp_path / "commands" / "alias.md").write_text("---\ndescription: a\n---\nalias body\n")
    (tmp_path / "skills" / "push.md").write_text("---\ndescription: old header-only skill\n---\n")
    with pytest.warns(DeprecationWarning, match="commands/ directory is deprecated"):
        bundle = load_bundle(canonical_root=tmp_path)
    by = {s.name: s for s in bundle.skills}
    assert by["push"].body == "command body"
    assert by["push"].description == "old header-only skill"
    assert by["push"].argument_hint == "x"
    assert by["alias"].body == "alias body"


def test_content_modules_relative_imports_resolve():
    """Every `from .x` / `from ..x` inside content/modules/ points at a file that exists.

    Catches a module move (chat_state -> chat/state, common/properties -> setup/properties, …)
    that missed updating an importer — the toolkit's own suite never imports content/ as a package.
    """
    modules_root = packaged_content_root() / "modules"
    broken = []
    for py in sorted(modules_root.rglob("*.py")):
        tree = ast.parse(py.read_text(), filename=str(py))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level == 0:
                continue
            base = py.parent
            for _ in range(node.level - 1):
                base = base.parent
            target = base / (node.module.replace(".", "/") if node.module else "")
            if target.with_suffix(".py").exists() or (target / "__init__.py").exists():
                continue
            broken.append(f"{py.relative_to(modules_root)}: from {'.' * node.level}{node.module or ''}")
    assert not broken, "unresolved relative imports in content/modules/:\n" + "\n".join(broken)


def test_local_overlay_wins_and_is_flagged(tmp_path):
    canonical = tmp_path / "content"
    (canonical / "skills").mkdir(parents=True)
    (canonical / "instructions").mkdir(parents=True)
    (canonical / "skills" / "push.md").write_text("---\ndescription: canonical\n---\nbody\n")

    local = tmp_path / ".local"
    (local / "skills").mkdir(parents=True)
    (local / "skills" / "push.md").write_text("---\ndescription: local override\n---\nlocal body\n")
    (local / "skills" / "mine.md").write_text("---\ndescription: repo-only\n---\nx\n")

    bundle = load_bundle(canonical_root=canonical, local_root=local)
    push = next(s for s in bundle.skills if s.name == "push")
    assert push.description == "local override"
    assert bundle.is_local("push")
    assert bundle.is_local("mine")
    assert bundle.layer_of("push") == "local"
