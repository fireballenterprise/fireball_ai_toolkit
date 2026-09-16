"""fireball_ai_toolkit — canonical AI-agent tooling and the generator that renders it per tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("fireball_ai_toolkit")
except PackageNotFoundError:  # running from a source checkout that isn't installed
    __version__ = "0+unknown"
