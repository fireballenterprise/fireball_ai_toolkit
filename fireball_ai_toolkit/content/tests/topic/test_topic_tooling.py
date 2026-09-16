"""Topic scaffolding + AGENTS.md generation — modules/topic/."""

from __future__ import annotations

import pytest
import yaml
from modules.toolkit.topic import init, reindex, switch, templates, update, update_list
from modules.toolkit.topic import list as topic_list

pytestmark = pytest.mark.topic


@pytest.fixture
def topics_root(tmp_path, monkeypatch):
    (tmp_path / "topics").mkdir()
    for module in (update_list, init, update, reindex, switch):
        monkeypatch.setattr(module, "get_repo_root", lambda: tmp_path, raising=False)
    return tmp_path


def _make_topic_dir(root, path: str) -> None:
    topic_dir = root / "topics" / path
    topic_dir.mkdir(parents=True, exist_ok=True)
    (topic_dir / "AGENTS.md").write_text(f"# {path}\n")


def _list_yml(root) -> dict:
    return yaml.safe_load((root / "topics" / "topics_list.yml").read_text())


class TestRenderAgentsMd:
    def test_includes_description_and_instruction_links(self):
        out = templates.render_agents_md("sidecar_vscode", "The extension topic.", ["sidecar", "sidecar_vscode"])
        assert "# Agent Instructions — sidecar_vscode" in out
        assert "The extension topic." in out
        assert "## Instructions" in out
        assert "[`sidecar`](../../.github/instructions/sidecar.instructions.md)" in out
        assert "[`sidecar_vscode`](../../.github/instructions/sidecar_vscode.instructions.md)" in out

    def test_nested_topic_gets_deeper_relative_path(self):
        out = templates.render_agents_md("a/b", instructions=["sidecar"])
        assert "(../../../.github/instructions/sidecar.instructions.md)" in out

    def test_deeply_nested_topic_gets_one_dotdot_per_segment(self):
        out = templates.render_agents_md("workshop/welding/tig/dcen", instructions=["sidecar"])
        # 4 path segments + 1 for topics/ = five `../`
        assert "(../../../../../.github/instructions/sidecar.instructions.md)" in out
        assert "# Agent Instructions — dcen" in out

    def test_no_instructions_section_when_none_given(self):
        out = templates.render_agents_md("plain")
        assert "## Instructions" not in out
        assert "- Chats: `chats/`" in out


class TestTopicMetaPersistence:
    def test_add_topic_stores_and_reads_back_meta(self, topics_root):
        update_list.add_topic("sidecar_chat", "The web app.", ["sidecar", "sidecar_chat"])
        assert update_list.list_topics() == ["sidecar_chat"]
        assert update_list.topic_meta("sidecar_chat") == {
            "description": "The web app.",
            "instructions": ["sidecar", "sidecar_chat"],
        }

    def test_add_topic_without_meta_leaves_existing_meta_intact(self, topics_root):
        update_list.add_topic("sidecar", "Umbrella.", ["sidecar"])
        update_list.add_topic("sidecar")  # re-register, no meta args
        assert update_list.topic_meta("sidecar")["description"] == "Umbrella."

    def test_plain_topic_has_no_meta_entry(self, topics_root):
        update_list.add_topic("amazon")
        assert update_list.topic_meta("amazon") == {}
        assert "topic_meta" not in _list_yml(topics_root)

    def test_write_is_yaml_round_trippable(self, topics_root):
        update_list.add_topic("sidecar", "Umbrella.", ["sidecar"])
        update_list.add_topic("amazon")
        data = _list_yml(topics_root)
        assert data["topics"] == ["amazon", "sidecar"]
        assert data["topic_meta"] == {"sidecar": {"description": "Umbrella.", "instructions": ["sidecar"]}}


class TestScaffoldAndUpdate:
    def test_scaffold_writes_agents_md_with_instruction_links(self, topics_root):
        topic_dir = topics_root / "topics" / "sidecar_llm"
        topic_dir.mkdir()
        init.scaffold(topic_dir, "sidecar_llm", "Local LLM.", ["sidecar", "sidecar_llm"])
        agents = (topic_dir / "AGENTS.md").read_text()
        assert "Local LLM." in agents
        assert "[`sidecar_llm`](../../.github/instructions/sidecar_llm.instructions.md)" in agents

    def test_update_regenerates_from_stored_meta(self, topics_root, monkeypatch):
        topic_dir = topics_root / "topics" / "sidecar_vscode"
        topic_dir.mkdir()
        init.scaffold(topic_dir, "sidecar_vscode", "Extension.", ["sidecar", "sidecar_vscode"])
        (topic_dir / "AGENTS.md").write_text("# clobbered by a human\n")

        monkeypatch.setattr(update.topic_active, "get_active_topic", lambda: "sidecar_vscode")
        update.main(dry_run=False, current_only=True)

        agents = (topic_dir / "AGENTS.md").read_text()
        assert "Extension." in agents
        assert "[`sidecar_vscode`](../../.github/instructions/sidecar_vscode.instructions.md)" in agents

    def test_split_instructions_parses_csv(self):
        assert init.split_instructions("sidecar, sidecar_chat ,sidecar_vscode") == [
            "sidecar",
            "sidecar_chat",
            "sidecar_vscode",
        ]
        assert init.split_instructions(None) is None
        assert init.split_instructions("") is None


class TestLegacyLayoutMigration:
    def _write_legacy(self, root, tree: dict) -> None:
        (root / "topics" / "topics_list.yml").write_text(yaml.safe_dump({"topics_layout": tree}))

    def test_load_flattens_nested_layout_to_paths(self, topics_root):
        self._write_legacy(
            topics_root,
            {"workshop": {"tig_welding": {}, "tools": {}}, "help": {"mac": {"vscode": {}}}, "travel": {}},
        )
        assert update_list.list_topics() == [
            "help/mac/vscode",
            "travel",
            "workshop/tig_welding",
            "workshop/tools",
        ]

    def test_topic_exists_works_off_migrated_layout(self, topics_root):
        self._write_legacy(topics_root, {"workshop": {"tig_welding": {}}})
        (topics_root / "topics" / "workshop" / "tig_welding").mkdir(parents=True)
        assert update_list.topic_exists("workshop/tig_welding")

    def test_next_write_drops_topics_layout_key(self, topics_root):
        self._write_legacy(topics_root, {"a": {}, "b": {}})
        update_list.add_topic("c")
        data = yaml.safe_load((topics_root / "topics" / "topics_list.yml").read_text())
        assert "topics_layout" not in data
        assert data["topics"] == ["a", "b", "c"]


class TestReindex:
    def test_registers_every_agents_md_dir_and_prunes_gone_ones(self, topics_root):
        for path in ("travel", "workshop/tig_welding", "workshop/welding/tig"):
            _make_topic_dir(topics_root, path)
        update_list.add_topic("stale/removed")  # in index, no directory

        reindex.main(dry_run=False)

        assert update_list.list_topics() == ["travel", "workshop/tig_welding", "workshop/welding/tig"]

    def test_preserves_topic_meta_for_survivors(self, topics_root):
        _make_topic_dir(topics_root, "sidecar_vscode")
        update_list.add_topic("sidecar_vscode", "Extension.", ["sidecar"])

        reindex.main(dry_run=False)

        assert update_list.topic_meta("sidecar_vscode") == {"description": "Extension.", "instructions": ["sidecar"]}

    def test_dry_run_does_not_write(self, topics_root):
        _make_topic_dir(topics_root, "travel")
        reindex.main(dry_run=True)
        assert not (topics_root / "topics" / "topics_list.yml").exists()


class TestSwitchSelfHeal:
    @pytest.fixture(autouse=True)
    def _repo_root(self, topics_root, monkeypatch):
        monkeypatch.setattr(switch.topic_active, "get_repo_root", lambda: topics_root, raising=False)

    def test_switch_registers_unindexed_but_real_topic(self, topics_root):
        _make_topic_dir(topics_root, "workshop/tig_welding")

        switch.main(path="workshop/tig_welding")

        assert "workshop/tig_welding" in update_list.list_topics()
        assert switch.topic_active.get_active_topic() == "workshop/tig_welding"

    def test_switch_errors_when_directory_absent(self, topics_root):
        with pytest.raises(SystemExit):
            switch.main(path="workshop/does_not_exist")


class TestListTree:
    def test_list_all_renders_indented_tree_with_active_star(self, topics_root, monkeypatch, capsys):
        for path in ("travel", "workshop/tig_welding", "workshop/tools"):
            update_list.add_topic(path)
        monkeypatch.setattr(topic_list.topic_active, "get_active_topic", lambda: "workshop/tig_welding")
        monkeypatch.setattr(topic_list.update_list, "get_repo_root", lambda: topics_root, raising=False)

        topic_list.main(show_all=True)

        out = capsys.readouterr().out
        assert "workshop/" in out
        assert "  tig_welding ⭐" in out
        assert "  tools" in out
