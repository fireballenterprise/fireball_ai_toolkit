"""`ai_toolkit` collection — the in-repo face of :mod:`fireball_ai_toolkit`.

Re-exports the task collection shipped inside the wheel (:mod:`fireball_ai_toolkit.tasks`)
so there's one definition. `ai_toolkit.{update,apply,upgrade,sync,contribute,check,release,
mdfix}` operate on the repo they're run from; `download`/`upload` are deprecated aliases. The
console script `ai-toolkit` (see `fireball_ai_toolkit/cli.py`) is the dependency-free
equivalent.
"""

from fireball_ai_toolkit.tasks import collection as namespace

__all__ = ["namespace"]
