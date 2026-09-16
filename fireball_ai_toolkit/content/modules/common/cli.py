"""Click-like CLI compatibility helpers backed by argparse."""

from __future__ import annotations

import argparse
import inspect
import logging
import os
import pathlib
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)


def is_tty() -> bool:
    """Return True when stdin is interactive."""
    return sys.stdin.isatty()


def style(text: Any, fg: str | None = None, bold: bool = False) -> str:
    """Return text unchanged (color/style intentionally ignored)."""
    del fg, bold
    return str(text)


def echo(message: str = "", *, err: bool = False) -> None:
    """Print a message to stdout/stderr."""
    print(message, file=sys.stderr if err else sys.stdout)


def secho(message: str, fg: str | None = None, bold: bool = False, *, err: bool = False) -> None:
    """Styled print helper compatible with click.secho."""
    echo(style(message, fg=fg, bold=bold), err=err)


class Choice:  # pylint: disable=too-few-public-methods
    """Simple callable choice validator for prompt(type=...)."""

    def __init__(self, choices: list[str], case_sensitive: bool = True) -> None:
        self.case_sensitive = case_sensitive
        self.choices = choices

    def __call__(self, value: str) -> str:
        for choice in self.choices:
            if self.case_sensitive and value == choice:
                return choice
            if not self.case_sensitive and value.lower() == choice.lower():
                return choice
        raise ValueError(f"Expected one of: {', '.join(self.choices)}")


class IntRange:  # pylint: disable=too-few-public-methods
    """Simple callable integer range validator for prompt(type=...)."""

    def __init__(self, min_value: int, max_value: int) -> None:
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value: str) -> int:
        parsed = int(value)
        if parsed < self.min_value or parsed > self.max_value:
            raise ValueError(f"Expected integer in range [{self.min_value}, {self.max_value}]")
        return parsed


class Path:  # pylint: disable=too-few-public-methods
    """Simple path type validator similar to click.Path."""

    def __init__(self, exists: bool = False) -> None:
        self.exists = exists

    def __call__(self, value: str) -> str:
        path = pathlib.Path(value)
        if self.exists and not path.exists():
            raise ValueError(f"Path does not exist: {value}")
        return value


def _coerce(value: str, value_type: type | object) -> object:
    if value_type is str:
        return value
    if value_type is int:
        return int(value)
    if value_type is float:
        return float(value)
    if callable(value_type):
        return value_type(value)
    return value


def _auto_confirm_enabled() -> bool:
    """Return True when confirmation prompts should be auto-accepted for scripts."""
    return os.environ.get("AUTO_CONFIRM", "").strip().lower() in {"1", "true", "yes", "y", "on"}


def prompt(
    label: str,
    *,
    default: object | None = None,
    show_default: bool = True,
    type: type | object = str,  # pylint: disable=redefined-builtin # noqa: A002
) -> Any:
    """Prompt for input in interactive terminals; use default when possible."""
    if not is_tty():
        if default is not None:
            return _coerce(str(default), type)
        raise RuntimeError(f"Prompt required in non-interactive mode: {label}")

    suffix = ""
    if show_default and default not in (None, ""):
        suffix = f" [{default}]"

    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if raw == "":
            if default is not None:
                return _coerce(str(default), type)
            continue
        try:
            return _coerce(raw, type)
        except TypeError:
            echo("Invalid input, please try again.", err=True)
        except ValueError:
            echo("Invalid input, please try again.", err=True)


def confirm(label: str, *, default: bool = False) -> bool:
    """Prompt yes/no in interactive terminals; use default in non-interactive mode."""
    if _auto_confirm_enabled() or not is_tty():
        return default

    hint = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{label} {hint}: ").strip().lower()
        if raw == "":
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        echo("Please answer yes or no.", err=True)


@dataclass
class _OptionSpec:  # pylint: disable=too-many-instance-attributes
    flags: list[str]
    dest: str
    default: Any
    required: bool
    is_flag: bool
    help_text: str | None
    value_type: Any
    dual_flag: tuple[str, str] | None


def option(*param_decls: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator compatible subset of click.option."""
    explicit_dest = next((d for d in param_decls if not d.startswith("-")), None)
    flags = [d for d in param_decls if d.startswith("-")]
    if not flags:
        raise ValueError("option() requires at least one flag declaration")

    dual_flag: tuple[str, str] | None = None
    expanded_flags: list[str] = []
    for flag in flags:
        if flag.startswith("--") and "/" in flag:
            left, right = flag.split("/", maxsplit=1)
            dual_flag = (left, right)
            expanded_flags.extend([left, right])
        else:
            expanded_flags.append(flag)

    long_flags = [f for f in expanded_flags if f.startswith("--")]
    if explicit_dest:
        dest = explicit_dest
    elif long_flags:
        dest = long_flags[0][2:].replace("-", "_")
    else:
        dest = expanded_flags[0].lstrip("-").replace("-", "_")

    spec = _OptionSpec(
        flags=expanded_flags,
        dest=dest,
        default=kwargs.get("default"),
        required=kwargs.get("required", False),
        is_flag=kwargs.get("is_flag", False),
        help_text=kwargs.get("help"),
        value_type=kwargs.get("type", str),
        dual_flag=dual_flag,
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        specs = getattr(func, "__cli_options__", [])
        specs.append(spec)
        func.__cli_options__ = specs
        return func

    return decorator


def _add_option(parser: argparse.ArgumentParser, spec: _OptionSpec) -> None:
    kwargs: dict[str, Any] = {"dest": spec.dest, "help": spec.help_text}

    if spec.dual_flag is not None:
        parser.set_defaults(**{spec.dest: spec.default if spec.default is not None else False})
        parser.add_argument(spec.dual_flag[0], action="store_true", dest=spec.dest, help=spec.help_text)
        parser.add_argument(spec.dual_flag[1], action="store_false", dest=spec.dest, help=argparse.SUPPRESS)
        return

    if spec.is_flag:
        kwargs["action"] = "store_true"
        kwargs["default"] = bool(spec.default) if spec.default is not None else False
        parser.add_argument(*spec.flags, **kwargs)
        return

    if spec.default is not None:
        kwargs["default"] = spec.default
    if spec.required:
        kwargs["required"] = True
    if spec.value_type is not None:
        kwargs["type"] = spec.value_type
    parser.add_argument(*spec.flags, **kwargs)


def _invoked_as_script() -> bool:
    """True only when reached via this module's own `if __name__ == "__main__": main()`.

    Distinguishes `python -m modules.x.y [--flags]` (where `sys.argv[1:]` are genuine CLI args
    for this command) from an in-process call like `some_module.main()` from an invoke task
    (where `sys.argv` still holds the invoke process's own argv, e.g. `['repo.pr_diff']` — parsing
    that as this command's own args raises a spurious "unrecognized arguments" error).
    """
    frame = inspect.currentframe()
    caller = frame.f_back.f_back if frame and frame.f_back else None
    return caller is not None and caller.f_globals.get("__name__") == "__main__"


def command() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator compatible subset of click.command."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        specs: list[_OptionSpec] = list(getattr(func, "__cli_options__", []))

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if args or kwargs:
                return func(*args, **kwargs)

            parser = argparse.ArgumentParser(prog=func.__name__, add_help=True)
            for spec in specs:
                _add_option(parser, spec)

            argv = sys.argv[1:]
            if not _invoked_as_script() and not any(arg.startswith("-") for arg in argv):
                argv = []
            parsed = parser.parse_args(argv)
            return func(**vars(parsed))

        wrapper.__cli_options__ = specs
        return wrapper

    return decorator
