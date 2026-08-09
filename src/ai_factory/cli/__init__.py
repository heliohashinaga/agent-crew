"""Thin workflow CLIs.

These CLIs compose libraries and the graphs; they contain no domain logic.
``spec_run`` and ``dev_run`` are wired as console scripts in
``pyproject.toml``.
"""

from ai_factory.cli.dev_run import main as dev_run_main
from ai_factory.cli.spec_run import main as spec_run_main

__all__ = ["dev_run_main", "spec_run_main"]
