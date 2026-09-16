"""modules.toolkit.backlog.common.scrub — the secret redactor every issue write passes through."""

import pytest
from modules.toolkit.backlog.common import scrub

pytestmark = pytest.mark.backlog

_REDACTION = "‹redacted›"


@pytest.mark.parametrize(
    "secret",
    [
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "token: sk-abc123def456ghi789",
        "Authorization: Bearer abcdefghijklmnop",
        "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "arn:aws:iam::123456789012:role/AdminRole",
        "postgres://user:hunter2@db.internal:5432/app",
    ],
)
def test_redacts_known_secret_shapes(secret):
    assert _REDACTION in scrub(secret)


def test_leaves_ordinary_prose_untouched():
    text = "The panel throws a 500 when the token is missing. See modules/aws/cdk/app.py:42."
    assert scrub(text) == text
