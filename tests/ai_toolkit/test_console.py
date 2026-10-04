"""Windows ANSI redirected streams must not crash setup output or Invoke docstrings."""

import os
import subprocess
import sys


def test_task_collection_configures_redirected_windows_output():
    # Load dependencies under the actual OS; emulate Windows only for the collection's
    # output setup so this regression runs on POSIX too, without mocking print/encoding.
    code = """
import importlib, os, sys
from fireball_ai_toolkit import tasks
sys.stdout.reconfigure(encoding='cp1252')
sys.stderr.reconfigure(encoding='cp1252')
sys.platform = 'win32'
importlib.reload(tasks)
print('\u2705 setup.properties \u2192 ready')
print('\u274c diagnostic', file=sys.stderr)
assert os.environ['PYTHONUTF8'] == '1'
assert os.environ['PYTHONIOENCODING'] == 'utf-8'
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, check=False,
                            env={**os.environ, "PYTHONIOENCODING": "cp1252"})
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stdout.decode("utf-8") == "✅ setup.properties → ready\n"
    assert "❌ diagnostic" in result.stderr.decode("utf-8")


def test_non_windows_output_settings_are_preserved(monkeypatch):
    from fireball_ai_toolkit import console

    monkeypatch.setattr(console.sys, "platform", "darwin")
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")
    console.configure_windows_output()
    assert os.environ["PYTHONIOENCODING"] == "ascii"
