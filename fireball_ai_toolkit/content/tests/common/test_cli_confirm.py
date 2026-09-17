"""Tests for the shared CLI confirmation helper."""

import builtins

import pytest
from modules.toolkit.common import cli

pytestmark = pytest.mark.common


def test_confirm_returns_default_when_auto_confirm_is_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTO_CONFIRM", "1")
    monkeypatch.setattr(cli, "is_tty", lambda: True)
    monkeypatch.setattr(
        builtins, "input", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("input should not be called"))
    )

    assert cli.confirm("Continue?", default=True) is True
