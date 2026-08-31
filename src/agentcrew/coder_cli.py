"""Thin CLI composing the coder->cleaner pipeline graph.

Mirrors the ``agentcrew-hello`` / ``agentcrew-llm`` CLI shape: exit codes
``0`` success, ``1`` usage, ``4`` runtime. It composes the library graph and
never holds business logic (constitution Principle I).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

from agentcrew.agents import cleaner as cleaner_agents
from agentcrew.agents import coder as coder_agents
from agentcrew.agents.clean_code_policy import read_clean_code_policy
from agentcrew.graphs.coder_cleaner import build_coder_cleaner_graph
from agentcrew.nodes import llm as llm_nodes

_USAGE = (
    "usage: agentcrew-code [--provider openrouter|opencode] "
    "[--model NAME] [--format text|json] <task>"
)

_PROVIDER_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "opencode": "OPENCODE_GO_API_KEY",
}


def _parse(argv: list[str]) -> tuple[dict[str, str], list[str]]:
    options: dict[str, str] = {}
    positionals: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--provider", "--model", "--format"):
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


def _build_graph(provider: str, model: str | None):
    coder_chat = coder_agents.default_chat(provider, model)
    cleaner_chat = cleaner_agents.default_chat(provider, model)
    return build_coder_cleaner_graph(
        coder_chat=coder_chat,
        cleaner_chat=cleaner_chat,
        provider=provider,
        model=model,
        # Honor the clean-code skill (SKILL.md) when present; else bundled policy.
        cleaner_policy=read_clean_code_policy(),
    )


def main(argv: Sequence[str] | None = None) -> int:
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

    if len(positionals) != 1:
        print("error: expected exactly one <task> argument", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 1
    task = positionals[0]

    if not llm_nodes.provider_api_key(provider):
        print(
            f"error: no API key configured for provider {provider!r}; "
            f"set {_PROVIDER_KEY_ENV[provider]} in your .env",
            file=sys.stderr,
        )
        return 4

    model = options.get("model")
    try:
        graph = _build_graph(provider, model)
        result = graph.invoke({"task": task})
    except ValueError:
        # Blank/whitespace-only task -> usage error.
        print("error: <task> must be non-empty", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps failures to exit 4
        print(f"error: pipeline failed: {exc}", file=sys.stderr)
        return 4

    if options.get("format", "text") == "json":
        print(
            json.dumps(
                {
                    "task": task,
                    "coder_output": result["coder_output"],
                    "cleaner_output": result["cleaner_output"],
                    "model": model or provider,
                }
            )
        )
    else:
        print(result["cleaner_output"])
    return 0


if __name__ == "__main__":
    sys.exit(main())