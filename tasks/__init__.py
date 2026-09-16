import sys
from pathlib import Path

from invoke import Collection

# Ensure the repo root (parent of tasks/) is importable so `modules.*` resolves
# regardless of how invoke was invoked.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from .ai_toolkit import namespace as ai_toolkit_namespace  # noqa: E402  # pylint: disable=wrong-import-position
from .common import debug, ruff, setup, versioning  # noqa: E402  # pylint: disable=wrong-import-position
from .common import main as common_main  # noqa: E402  # pylint: disable=wrong-import-position
from .tests import namespace as tests_namespace  # noqa: E402  # pylint: disable=wrong-import-position

namespace = Collection(auto_dash_names=False)

# Inherited from template_python: `common/` + `tests/` (debug/ruff/setup + fix/test aliases, plus
# the tests themselves), each registered at its original top-level name (`debug.*`, `ruff.*`,
# `setup.*`, `tests.*`, bare `fix`/`test`). `ai_toolkit/` is this repo's own reason to exist —
# the canonical-content sync (`ai_toolkit.{update,apply,upgrade,sync,contribute,check,release}`).
namespace.add_collection(ai_toolkit_namespace, name="ai_toolkit")
namespace.add_collection(debug, name="debug")
namespace.add_collection(ruff, name="ruff")
namespace.add_collection(setup, name="setup")
namespace.add_collection(tests_namespace, name="tests")
namespace.add_collection(Collection.from_module(versioning, auto_dash_names=False), name="ver")

namespace.add_task(common_main.fix, name="fix")
namespace.add_task(common_main.test, name="test")
