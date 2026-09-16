"""Drift gate — every docs/change_logs/<category>/<name>.md must already lead with the entry
properties.yml's current version/latest_changes requires. See changelogs.instructions.md.

`check_each_log(update=False)` raises `ValueError` itself on the first stale entry it finds
(rather than returning a list to assert on) — see `modules/docs/lib/change_logs.py` — so this test
just calls it and lets that propagate as the failure. A no-op when properties.yml has no `changelogs:` key.
"""

import pytest
from modules.toolkit.docs.lib.change_logs import check_each_log

pytestmark = pytest.mark.drift


def test_changelogs_current():
    check_each_log(update=False)
