"""Tests for the shared `verbatim()` output-fencing helper."""

import pytest
from modules.toolkit.common.utils import verbatim

pytestmark = pytest.mark.common


def test_wraps_markdown_in_sidecar_markers() -> None:
    out = verbatim("## Title\n\n| a | b |")
    assert out == "<!--sidecar:verbatim-->\n## Title\n\n| a | b |\n<!--sidecar:/verbatim-->"


def test_strips_surrounding_whitespace_from_the_payload() -> None:
    assert verbatim("\n\n  body  \n\n") == "<!--sidecar:verbatim-->\nbody\n<!--sidecar:/verbatim-->"


def test_markers_are_html_comments_so_a_plain_renderer_ignores_them() -> None:
    out = verbatim("x")
    assert out.startswith("<!--") and out.rstrip().endswith("-->")
