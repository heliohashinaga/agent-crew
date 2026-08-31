"""Thin CLI that composes the agentcrew hello-world node.

The CLI holds no business logic — it parses arguments, delegates to the library
node, formats output (human-readable or JSON), and maps results to exit codes.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

from dotenv import load_dotenv

from agentcrew.nodes.hello_world import build_hello_world_node

_USAGE = "usage: agentcrew-hello [hello] <text> [--format text|json]"

# Load optional LANGSMITH_* (and other) vars from a local .env if present.
# Does not override already-set environment variables. Runs before any
# LangSmith tracing is initialized so a filled .env takes effect.
load_dotenv()


def _parse_format(argv: list[str]) -> tuple[str, list[str]]:
    """Split ``argv`` into (format, positionals), tolerating ``--format`` anywhere."""
    fmt = "text"
    positionals: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--format":
            if i + 1 >= len(argv):
                raise ValueError("--format requires a value")
            fmt = argv[i + 1]
            i += 2
        elif arg.startswith("--format="):
            fmt = arg.split("=", 1)[1]
            i += 1
        else:
            positionals.append(arg)
            i += 1
    return fmt, positionals


def main(argv: Sequence[str] | None = None) -> int:
    """Run the hello-world CLI entry point and return an exit code.

    Exit codes: 0 success, 1 usage error, 4 unexpected runtime failure.
    """
    raw_args = list(sys.argv[1:] if argv is None else argv)

    try:
        fmt, positionals = _parse_format(raw_args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 1

    # Tolerate an optional leading `hello` verb.
    if positionals and positionals[0] == "hello":
        positionals = positionals[1:]

    if len(positionals) != 1:
        print("error: expected exactly one <text> argument", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 1

    text = positionals[0]
    node = build_hello_world_node()
    try:
        result = node.invoke(text)
    except ValueError:
        # Empty/whitespace-only input -> usage error.
        print("error: <text> must be non-empty", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 - CLI boundary maps unexpected failures to exit 4
        print("error: unexpected failure", file=sys.stderr)
        return 4

    if fmt == "json":
        print(json.dumps({"input": result["input"], "greeting": result["greeting"]}))
    else:
        print(result["greeting"])
    return 0


if __name__ == "__main__":
    sys.exit(main())