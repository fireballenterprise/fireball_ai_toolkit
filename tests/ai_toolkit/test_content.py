"""Parsing the canonical content trees and a local overlay."""

import ast

import pytest

from fireball_ai_toolkit.catalog import load_bundle, packaged_ai_root, packaged_content_root

pytestmark = pytest.mark.ai_toolkit


def test_packaged_bundle_parses():
    bundle = load_bundle(canonical_root=packaged_ai_root())
    assert bundle.commands, "expected canonical commands"
    assert bundle.instructions, "expected canonical instructions"
    assert all(c.slug for c in bundle.commands)
    assert all(origin == "shared" for origin in bundle.origin.values())


def test_every_command_is_wired_to_a_skill():
    """Every canonical command appears in at least one skill's `commands:` list.

    Most commands have a same-named skill; alias / sub-verb commands (``add_bug``,
    ``pr-notes``, …) ride on a parent skill's list instead.
    """
    bundle = load_bundle(canonical_root=packaged_ai_root())
    skills = {s.name: s for s in bundle.skills}
    wired = {path for skill in bundle.skills for path in skill.commands}
    for command in bundle.commands:
        ref = f".fireball_ai_toolkit/commands/{command.slug}.md"
        assert ref in wired, f"command {command.slug!r} is in no skill's commands: list"
        if command.slug in skills:
            assert ref in skills[command.slug].commands


def test_skill_instruction_and_command_paths_resolve():
    """Every path in a canonical skill's `instructions:` / `commands:` list is a real file."""
    ai_root = packaged_ai_root()
    bundle = load_bundle(canonical_root=ai_root)
    missing = []
    for skill in bundle.skills:
        for path in (*skill.instructions, *skill.commands):
            rel = path.removeprefix(".fireball_ai_toolkit/")
            if not (ai_root / rel).is_file():
                missing.append(f"{skill.name}: {path}")
    assert not missing, "skill paths that do not resolve:\n" + "\n".join(missing)


def test_command_exec_line_extracted():
    bundle = load_bundle(canonical_root=packaged_ai_root())
    push = next((c for c in bundle.commands if c.slug == "push"), None)
    assert push is not None
    assert push.exec_line.startswith("uv run")


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
    (canonical / "commands").mkdir(parents=True)
    (canonical / "instructions").mkdir(parents=True)
    (canonical / "commands" / "push.md").write_text("---\ndescription: canonical\n---\nbody\n")

    local = tmp_path / ".local"
    (local / "commands").mkdir(parents=True)
    (local / "commands" / "push.md").write_text("---\ndescription: local override\n---\nlocal body\n")
    (local / "commands" / "mine.md").write_text("---\ndescription: repo-only\n---\nx\n")

    bundle = load_bundle(canonical_root=canonical, local_root=local)
    push = next(c for c in bundle.commands if c.slug == "push")
    assert push.description == "local override"
    assert bundle.is_local("push")
    assert bundle.is_local("mine")
    assert bundle.layer_of("push") == "local"
