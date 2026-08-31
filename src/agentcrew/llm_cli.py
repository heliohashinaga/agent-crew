"""Thin CLI that composes the LLM-backed node.

Mirrors the ``agentcrew-hello`` CLI shape (same exit codes: 0 success, 1 usage,
4 unexpected failure), but calls the networked LLM node. Requires an API key for
the chosen provider (``OPENROUTER_API_KEY`` for ``openrouter``,
``OPENCODE_GO_API_KEY`` for ``opencode``) via the local ``.env`` / environment.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

from agentcrew.nodes import llm as llm_nodes
from agentcrew.nodes.llm import build_llm_node

_USAGE = (
    "usage: agentcrew-llm [--provider openrouter|opencode] "
    "[--model NAME] [--format text|json] <text>"
)

_PROVIDER_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "opencode": "OPENCODE_GO_API_KEY",
}


def _parse(argv: list[str]) -> tuple[dict[str, str], list[str]]:
    """Split ``argv`` into (options, positionals), tolerating flags anywhere."""
    options: dict[str, str] = {}
    positionals: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--provider" or arg == "--model" or arg == "--format":
            if i + 1 >= len(argv):
                raise ValueError(f"{arg} requires a value")
            options[arg[2:]] = argv[i + 1]
            i += 2
        elif arg.startswith("--provider="):
            options["provider"] = arg.split("=", 1)[1]
            i += 1
        elif arg.startswith("--model="):
            options["model"] = arg.split("=", 1)[1]
            i += 1
        elif arg.startswith("--format="):
            options["format"] = arg.split("=", 1)[1]
            i += 1
        else:
            positionals.append(arg)
            i += 1
    return options, positionals


def main(argv: Sequence[str] | None = None) -> int:
    """Run the LLM CLI entry point and return an exit code.

    Exit codes: 0 success, 1 usage error, 4 unexpected runtime failure.
    """
    raw_args = list(sys.argv[1:] if argv is None else argv)

    try:
        options, positionals = _parse(raw_args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 1

    provider = options.get("provider", "openrouter")
    if provider not in _PROVIDER_KEY_ENV:
        print(f"error: unsupported provider {provider!r}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 1

    fmt = options.get("format", "text")

    if len(positionals) != 1:
        print("error: expected exactly one <text> argument", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 1
    text = positionals[0]

    # Fail fast with a clear hint when the provider has no API key configured.
    if not llm_nodes.provider_api_key(provider):
        print(
            f"error: no API key configured for provider {provider!r}; "
            f"set {_PROVIDER_KEY_ENV[provider]} in your .env",
            file=sys.stderr,
        )
        return 4

    try:
        node = build_llm_node(provider, model=options.get("model"), cached=False)
        result = node.invoke(text)
    except ValueError:
        # Empty/whitespace-only input -> usage error.
        print("error: <text> must be non-empty", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps failures to exit 4
        print(f"error: LLM call failed: {exc}", file=sys.stderr)
        return 4

    if fmt == "json":
        print(json.dumps(result))
    else:
        print(result["response"])
    return 0


if __name__ == "__main__":
    sys.exit(main())