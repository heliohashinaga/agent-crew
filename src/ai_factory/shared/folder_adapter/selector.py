"""Task selector parsing (002-folder-dev-run, T053/T054, FR-014b).

Parses the CLI ``[<selector>]`` argument into an explicit set of task IDs.
Supported forms:

* ``T3``           — single task
* ``T3,T5``        — comma-separated list
* ``T3-T7``        — inclusive range
* ``T3-``          — open range to the last task
* ``*`` / ``all``  — every task

Unknown task IDs are a hard error (non-zero exit). Purely deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

Single = re.compile(r"^T(\d+)$", re.IGNORECASE)
Range = re.compile(r"^T(\d+)\s*-\s*(?:T?(\d+))$", re.IGNORECASE)
OpenRange = re.compile(r"^T(\d+)\s*-\s*$", re.IGNORECASE)


class SelectorError(Exception):
    """Raised when a selector cannot be parsed or references an unknown ID."""


@dataclass(frozen=True)
class TaskRange:
    start: int
    end: int | None = None


@dataclass(frozen=True)
class TaskSelector:
    """A parsed and resolved selector."""

    ranges: list[TaskRange] = field(default_factory=list)
    all: bool = False

    def includes(self, task_id: str) -> bool:
        if self.all:
            return True
        m = re.match(r"^T(\d+)$", task_id, re.IGNORECASE)
        if not m:
            return False
        num = int(m.group(1))
        return any(
            (r.start <= num and (r.end is None or num <= r.end)) for r in self.ranges
        )


def parse_selector(selector: str) -> TaskSelector:
    """Parse a raw CLI selector string into an explicit TaskSelector."""
    if selector is None:
        raise SelectorError("Selector required.")
    s = selector.strip()
    if not s:
        raise SelectorError("Empty selector.")
    if s in ("*", "all"):
        return TaskSelector(all=True)

    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        raise SelectorError(f"Malformed selector '{selector}'.")
    ranges: list[TaskRange] = []
    for part in parts:
        m = Range.match(part)
        if m:
            ranges.append(TaskRange(start=int(m.group(1)), end=int(m.group(2))))
            continue
        m = OpenRange.match(part)
        if m:
            ranges.append(TaskRange(start=int(m.group(1)), end=None))
            continue
        m = Single.match(part)
        if m:
            ranges.append(TaskRange(start=int(m.group(1)), end=int(m.group(1))))
            continue
        raise SelectorError(
            f"Unsupported task selector '{part}'. "
            "Use T###, T3,T5, T3-T7, T3-, * or all."
        )
    return TaskSelector(ranges=ranges)


def resolve_selector(selector: str, available_ids: list[str]) -> TaskSelector:
    """Resolve a selector against known task IDs, raising on unknown references."""
    sel = parse_selector(selector)
    if sel.all:
        return sel
    known = {re.sub(r"^T", "", i, flags=re.IGNORECASE): i for i in available_ids}
    known_nums = {int(k) for k in known}
    found: list[TaskRange] = []
    for r in sel.ranges:
        # Validate start bound exists (or open range sentinel).
        if r.start not in known_nums:
            raise SelectorError(
                f"Unknown task T{r.start}. "
                "Selector references a task not in tasks.md."
            )
        # Narrow the range to known IDs (open range ends at the last known).
        end = r.end
        if end is None:
            end = max(known_nums)
        present = {n for n in known_nums if r.start <= n <= end}
        if not present:
            raise SelectorError(f"Range T{r.start}-T{end} selects no known tasks.")
        found.append(TaskRange(start=min(present), end=max(present)))
    return TaskSelector(ranges=found)


__all__ = [
    "SelectorError",
    "TaskRange",
    "TaskSelector",
    "parse_selector",
    "resolve_selector",
]
