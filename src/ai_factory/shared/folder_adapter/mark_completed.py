"""tasks.md completion write-back (002-folder-dev-run, T016/T017, FR-010).

Marks a task ``T###`` as done (``[ ]`` → ``[x]``) in ``tasks.md`` while leaving
every other line byte-identical. This is the factory-owned completion record;
the factory never delegates this side effect to external skills. Purely
deterministic and line-preserving.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TASK_RE = re.compile(r"^(\s*[*\-0-9. ]*\s*\[[ ]*)([ xX])(\]\s+)(T\d+\b)")


@dataclass(frozen=True)
class MarkResult:
    """Outcome of marking a task complete."""

    content: str
    changed: bool
    task_id: str
    matched: bool


def mark_task_complete(content: str, task_id: str, done: bool = True) -> MarkResult:
    """Return content with ``task_id`` marked done (or undone if ``done`` is False)."""
    target = task_id.upper().strip()
    mark = "x" if done else " "
    lines = content.splitlines()
    changed = False
    matched = False
    for i, line in enumerate(lines):
        m = TASK_RE.match(line)
        if m and m.group(4).upper() == target:
            matched = True
            if m.group(2) != mark:
                new_line = f"{m.group(1)}{mark}{m.group(3)}{m.group(4)}{line[m.end():]}"
                lines[i] = new_line
                changed = True
    return MarkResult(
        content="\n".join(lines),
        changed=changed,
        task_id=target,
        matched=matched,
    )


__all__ = ["MarkResult", "mark_task_complete"]
