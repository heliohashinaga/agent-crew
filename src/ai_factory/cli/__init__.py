"""Thin workflow CLIs.

These CLIs compose libraries and the graphs; they contain no domain logic.
``dev-run`` is the single folder-driven entry point (FR-006); the removed
``spec-run`` console script was the prior two-step entry.
"""

from ai_factory.cli.dev_run import main as dev_run_main

__all__ = ["dev_run_main"]
