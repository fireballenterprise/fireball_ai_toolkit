"""UTF-8 output for native Windows task discovery, including redirected logs."""

import os
import sys


def configure_windows_output() -> None:
    """Avoid cp1252 encode failures without persisting machine/user configuration.

    Python's Windows console is Unicode, but redirected handles may use the ANSI codepage.
    Invoke prints task docstrings itself, so configure once while loading its collection,
    before either Invoke or a task emits Unicode. Child Python processes inherit UTF-8.
    """
    if sys.platform != "win32":
        return
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
