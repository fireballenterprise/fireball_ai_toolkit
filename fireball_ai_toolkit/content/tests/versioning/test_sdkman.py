"""modules.toolkit.versioning.sdkman — .sdkmanrc parsing, `sdk list` latest-pick, the skip-list."""

import pytest
from modules.toolkit.versioning import sdkman

pytestmark = pytest.mark.versioning


def _write_sdkmanrc(tmp_path, text):
    (tmp_path / ".sdkmanrc").write_text(text, encoding="utf-8")
    return tmp_path


def test_read_sdkmanrc_parses_key_value_lines(tmp_path):
    root = _write_sdkmanrc(tmp_path, "# a comment\njava=26.0.2-tem\ngradle=9.7.0\n\n#kotlin=skip\n")
    assert sdkman.read_sdkmanrc(root) == {"java": "26.0.2-tem", "gradle": "9.7.0"}


def test_read_sdkmanrc_missing_file_is_empty(tmp_path):
    assert sdkman.read_sdkmanrc(tmp_path) == {}


def test_skip_list_seeds_gradle_971_and_reads_inline_comments(tmp_path):
    root = _write_sdkmanrc(
        tmp_path, "gradle=9.7.0\n# sdkman-skip: gradle 9.7.3 9.7.4\n# sdkman-skip: java 27.0.0-tem\n"
    )
    skip = sdkman.read_skip_list(root)
    assert skip["gradle"] == {"9.7.1", "9.7.3", "9.7.4"}
    assert skip["java"] == {"27.0.0-tem"}


def test_channel_suffix_and_version_key():
    assert sdkman._channel_suffix("26.0.2-tem") == "-tem"
    assert sdkman._channel_suffix("9.7.0") == ""
    assert sdkman._version_key("26.0.2-tem") == (26, 0, 2)
    assert sdkman._version_key("9.7.0") == (9, 7, 0)


def test_latest_identifier_picks_newest_same_channel_non_prerelease(monkeypatch):
    monkeypatch.setattr(
        sdkman,
        "available_identifiers",
        lambda _c: ["25.0.4-tem", "26.0.2-tem", "27.0.0+ea.13-open", "28.0.0-ea", "26.0.1-amzn"],
    )
    # current 25.0.4-tem -> newest -tem that isn't a pre-release
    assert sdkman.latest_identifier("java", "25.0.4-tem", set()) == "26.0.2-tem"


def test_latest_identifier_skips_the_skip_list(monkeypatch):
    monkeypatch.setattr(sdkman, "available_identifiers", lambda _c: ["9.7.0", "9.7.1", "9.7.0-rc-3"])
    # 9.7.1 is corrupt-via-SDKMAN and skipped; 9.7.0-rc-3 is a pre-release -> nothing newer than 9.7.0
    assert sdkman.latest_identifier("gradle", "9.7.0", {"9.7.1"}) is None
    # once 9.7.2 lands it's picked
    monkeypatch.setattr(sdkman, "available_identifiers", lambda _c: ["9.7.0", "9.7.1", "9.7.2"])
    assert sdkman.latest_identifier("gradle", "9.7.0", {"9.7.1"}) == "9.7.2"


def test_latest_identifier_none_when_already_current(monkeypatch):
    monkeypatch.setattr(sdkman, "available_identifiers", lambda _c: ["2.3.21", "2.4.0", "2.4.10"])
    assert sdkman.latest_identifier("kotlin", "2.4.10", set()) is None


def test_bump_gradle_wrapper_rewrites_distribution_url(tmp_path):
    wrapper = tmp_path / "gradle" / "wrapper"
    wrapper.mkdir(parents=True)
    props = wrapper / "gradle-wrapper.properties"
    props.write_text(
        "distributionUrl=https\\://services.gradle.org/distributions/gradle-9.7.0-bin.zip\n", encoding="utf-8"
    )
    assert sdkman.bump_gradle_wrapper(tmp_path, "9.7.2") is True
    assert "gradle-9.7.2-bin.zip" in props.read_text(encoding="utf-8")
    assert sdkman.bump_gradle_wrapper(tmp_path, "9.7.2") is False  # already there


def test_bump_gradle_wrapper_no_file(tmp_path):
    assert sdkman.bump_gradle_wrapper(tmp_path, "9.7.2") is False


def test_main_exits_3_without_sdkmanrc(monkeypatch, tmp_path):
    monkeypatch.setattr(sdkman, "get_repo_local", lambda: tmp_path)
    with pytest.raises(SystemExit) as exc:
        sdkman.main(dry_run=True, no_confirm=True)
    assert exc.value.code == 3


def test_main_dry_run_reports_and_does_not_write(monkeypatch, tmp_path):
    root = _write_sdkmanrc(tmp_path, "java=25.0.4-tem\ngradle=9.7.0\n")
    monkeypatch.setattr(sdkman, "get_repo_local", lambda: root)
    monkeypatch.setattr(
        sdkman,
        "available_identifiers",
        lambda candidate: ["26.0.2-tem"] if candidate == "java" else ["9.7.0", "9.7.1"],
    )
    sdkman.main(dry_run=True, no_confirm=True)  # no SystemExit — updates available, dry-run returns
    assert "25.0.4-tem" in (root / ".sdkmanrc").read_text(encoding="utf-8")  # unchanged


def test_main_apply_rewrites_sdkmanrc(monkeypatch, tmp_path):
    root = _write_sdkmanrc(tmp_path, "java=25.0.4-tem\ngradle=9.7.0\n")
    monkeypatch.setattr(sdkman, "get_repo_local", lambda: root)
    monkeypatch.setattr(
        sdkman,
        "available_identifiers",
        lambda candidate: ["26.0.2-tem"] if candidate == "java" else ["9.7.0", "9.7.1"],
    )
    sdkman.main(dry_run=False, no_confirm=True)
    text = (root / ".sdkmanrc").read_text(encoding="utf-8")
    assert "java=26.0.2-tem" in text
    assert "gradle=9.7.0" in text  # 9.7.1 skipped, stays put
