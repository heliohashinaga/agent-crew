"""Thin workflow CLIs.

These CLIs compose libraries and the graphs; they contain no domain logic.
`spec_run` is wired as the ``spec-run`` console script in ``pyproject.toml``.
"""

from ai_factory.cli.spec_run import main

__all__ = ["main"]
