"""CLI-convention audit (T084/T089, contracts/library-cli-convention.md).

An automated sweep over EVERY library and workflow CLI asserting the
shared convention: each exposes a ``main`` callable, builds a parser with
``--format`` (choices ``json``/``human``, default ``json``), and imports
cleanly. This turns the convention into a check that any new CLI must
satisfy.
"""

from __future__ import annotations

import importlib
import pathlib

import pytest

CLI_MODULES = [
    # Spec workflow roles
    "ai_factory.spec_workflow.spec_agent.cli",
    "ai_factory.spec_workflow.requirements_reviewer.cli",
    # Dev workflow roles
    "ai_factory.dev_workflow.technical_planner.cli",
    "ai_factory.dev_workflow.orchestrator.cli",
    "ai_factory.dev_workflow.code_worker.cli",
    "ai_factory.dev_workflow.code_reviewer.cli",
    "ai_factory.dev_workflow.test_engineer.cli",
    "ai_factory.dev_workflow.test_runner.cli",
    "ai_factory.dev_workflow.security_reviewer.cli",
    # Shared library CLIs
    "ai_factory.shared.telemetry.cli",
    "ai_factory.shared.folder_adapter.cli",
    # Workflow CLIs
    "ai_factory.cli.dev_run",
]


@pytest.mark.parametrize("module_name", CLI_MODULES)
def test_cli_exposes_main_and_build_parser(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert callable(mod.main)
    assert callable(mod.build_parser)


@pytest.mark.parametrize("module_name", CLI_MODULES)
def test_cli_format_arg_contract(module_name: str) -> None:
    """T084: --format must accept json+human and default to json."""
    mod = importlib.import_module(module_name)
    parser = mod.build_parser()
    for action in parser._actions:  # noqa: SLF001 - argparse internals
        if action.option_strings and "--format" in action.option_strings:
            assert set(action.choices) == {"json", "human"}
            assert action.default == "json"
            return
    pytest.fail(f"{module_name} does not register a --format argument")


@pytest.mark.parametrize("module_name", CLI_MODULES)
def test_cli_module_is_importable(module_name: str) -> None:
    # Importing must not hit the network or execute domain logic.
    importlib.import_module(module_name)


def test_all_clis_are_listed() -> None:
    """Every ``cli`` entry point in the source tree is covered by this audit."""
    root = pathlib.Path("src/ai_factory")
    found: set[str] = set()
    # Library CLIs: modules named cli.py (e.g. dev_workflow/code_reviewer/cli.py).
    for p in root.rglob("cli.py"):
        rel = p.relative_to("src").with_suffix("")
        found.add(str(rel).replace("/", "."))
    # Workflow CLIs: the cli package holds spec_run/dev_run modules.
    for p in (root / "cli").glob("*.py"):
        if p.stem != "__init__":
            found.add(f"ai_factory.cli.{p.stem}")
    missing = sorted(found - set(CLI_MODULES))
    assert not missing, f"CLIs not covered by the audit: {missing}"
