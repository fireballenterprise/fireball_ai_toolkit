"""get_properties() follows the checkout that is actually running — a second family clone (e.g. an
automation worker's) must resolve its own siblings, never the primary checkout's."""

import pytest
from modules.fireball_ai_toolkit.setup import properties

pytestmark = pytest.mark.setup


def _props(home):
    return {
        "repo": {"local": f"{home}/Development/acme/tool"},
        "repos_local": {"acme": f"{home}/Development/acme", "other": f"{home}/Development/other"},
    }


def test_primary_checkout_is_unchanged(tmp_path):
    root = tmp_path / "Development" / "acme" / "tool"
    root.mkdir(parents=True)
    props = properties._relocate_to_checkout(_props(tmp_path), root)  # pylint: disable=protected-access
    assert props["repo"]["local"] == f"{tmp_path}/Development/acme/tool"
    assert props["repos_local"]["acme"] == f"{tmp_path}/Development/acme"


def test_second_clone_resolves_its_own_family(tmp_path):
    (tmp_path / "Development" / "acme").mkdir(parents=True)
    clone = tmp_path / "workers" / "dev-1" / "acme" / "tool"
    clone.mkdir(parents=True)
    props = properties._relocate_to_checkout(_props(tmp_path), clone)  # pylint: disable=protected-access
    assert props["repo"]["local"] == str(clone.resolve())
    assert props["repos_local"]["acme"] == str(clone.parent.resolve())
    # An unrelated org base is left alone.
    assert props["repos_local"]["other"] == f"{tmp_path}/Development/other"


def test_env_override_still_wins(tmp_path, monkeypatch):
    clone = tmp_path / "workers" / "dev-1" / "acme" / "tool"
    clone.mkdir(parents=True)
    (clone / "properties.yml").write_text(
        f"repo:\n  local: {tmp_path}/Development/acme/tool\nrepos_local:\n  acme: {tmp_path}/Development/acme\n"
    )
    monkeypatch.setenv(properties.REPO_ROOT_ENV, str(clone))
    properties.get_repo_root.cache_clear()
    properties.get_properties.cache_clear()
    try:
        assert properties.get_properties()["repos_local"]["acme"] == f"{tmp_path}/Development/acme"
    finally:
        properties.get_repo_root.cache_clear()
        properties.get_properties.cache_clear()
