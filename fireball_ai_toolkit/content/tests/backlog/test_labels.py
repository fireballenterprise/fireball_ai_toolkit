"""modules.toolkit.backlog.common — area / colour label helpers."""

from pathlib import Path

import pytest
from modules.toolkit.backlog import common
from modules.toolkit.backlog.common import area_for_repo, label_color
from modules.toolkit.setup.properties import FamilyRepo

pytestmark = pytest.mark.backlog


def _repo(name, org="fireballenterprise"):
    return FamilyRepo(
        org=org,
        name=name,
        path=Path("/nonexistent") / name,
        is_self=False,
        exists=False,
        default_branch="main",
        parent=None,
        status="active",
        visibility="private",
        ai=False,
        use_ci=False,
        pull_request=False,
        purpose="",
    )


@pytest.mark.parametrize(
    ("name", "area"),
    [
        ("fireball_sidecar_vscode", "Sidecar VSCode"),
        ("fireball_ai_toolkit", "AI Toolkit"),
        ("fireball_orchestrator", "Orchestrator"),
        ("fireball_gear_shopify", "Gear Shopify"),
        ("template_ai_python", "AI Python"),
        ("workflows_shopify", "Workflows Shopify"),
    ],
)
def test_area_for_repo(name, area):
    assert area_for_repo(_repo(name)) == area


def test_label_color_is_stable_and_in_palette():
    first = label_color("backlog")
    assert first == label_color("Backlog") == label_color("  backlog ")
    assert first in common._LABEL_PALETTE
    assert len(first) == 6


def test_label_color_spreads_across_the_palette():
    colours = {label_color(name) for name in ("backlog", "router", "Sidecar VSCode", "Regression", "UI", "topics")}
    assert len(colours) > 1
