"""Toolchain-aware lint / format / test running for the toolkit and every repo it manages.

``tests.style`` and ``tests.unit`` are the two entry points (behind ``invoke tests.style`` /
``invoke tests.unit`` and the bare ``invoke fix`` / ``invoke test`` aggregates). Each inspects the
repo's toolchains (``common.toolchains``) and runs only the tools that apply — so pointing them at
another repo with ``--repo`` Just Works.

One module per tool (``ruff``, ``pylint``, ``yamllint``, ``actionlint``, ``ktlint``, ``detekt``,
``android_lint``, ``pytest``, ``gradle_unit``); each exposes ``applies(root) -> bool`` and
``check(root) -> ToolResult`` (plus ``fix(root)`` where the tool can autofix).
"""
