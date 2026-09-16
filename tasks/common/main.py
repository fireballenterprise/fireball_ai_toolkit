from pathlib import Path

from invoke import task

from fireball_ai_toolkit.mdfix import check_tree as md_check
from fireball_ai_toolkit.mdfix import fix_tree as md_fix

from ..tests import actionlint, pylint, pytest, rufflint, yamllint
from . import ruff


@task
def fix(context):
    """Run All Automated Fixes"""
    ruff.fix(context)
    ruff.format(context)
    changed = md_fix(Path.cwd(), write=True)
    print(f"Normalised {len(changed)} markdown file(s).")


@task
def test(context):
    """Run All Tests"""
    actionlint(context)
    md_check(Path.cwd())
    pylint(context)
    pytest(context)
    rufflint(context)
    yamllint(context)
