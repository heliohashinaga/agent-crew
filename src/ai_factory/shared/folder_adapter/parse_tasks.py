"""tasks.md parsing (002-folder-dev-run, T008–T011).

Maps ``tasks.md`` units to :class:`TechnicalSubtask` (``title``, ``description``,
``files``, ``acceptance_criteria``, ``source_task_id`` ``source_task_type``),
preserving checklist order and detecting shared-file non-parallel conflicts
(FR-013). Path normalization drops absolute host paths and out-of-repo
references with a warning (FR-008) and flags shared-file non-parallel pairs
(SC-003). Purely deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ai_factory.dev_workflow.technical_planner.planner import TechnicalSubtask

TASK_RE = re.compile(r"^\s*(?:[-*\d]+\.?)?\s*\[\s*([ xX])\s*\]\s+(T\d+)\s*(.*)$")
FILE_RE = re.compile(r"^\s*-?\s*File\s*:\s*(.+)$", re.IGNORECASE)
AC_RE = re.compile(r"^\s*-\s+[^T][^-]*?\[[ xX]\]\s*(.+)$")
SHARED_RE = re.compile(r"[\\/ ]+")

# Artifacts produced by test-build/test-run phases are considered non-source.
_IMPL_SUFFIXES = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".c", ".h",
    ".cpp", ".sql", ".sh", ".toml", ".md", ".json", ".yaml", ".yml", ".ini", ".cfg",
)


@dataclass(frozen=True)
class NormalizedFile:
    """A file path after normalization against the repo root."""

    path: str
    dropped: bool = False
    warning: str = ""


@dataclass(frozen=True)
class SharedFileConflict:
    """Two tasks that both touch a file but are not both parallel-safe."""

    source_task_id_a: str
    source_task_id_b: str
    file: str


@dataclass(frozen=True)
class ParseTasksResult:
    """Result of parsing ``tasks.md``."""

    subtasks: list[TechnicalSubtask] = field(default_factory=list)
    conflicts: list[SharedFileConflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_file_paths(file_specs: list[str], repo_root: str = "") -> NormalizedFile:
    """Normalize a single file path, dropping absolute/out-of-repo references."""
    raw = file_specs[0].strip() if file_specs else ""
    # Strip surrounding backticks/quotes and trailing parenthetical comments.
    clean = raw.strip("`'")
    clean = re.sub(r"\s*\([^)]*\)\s*$", "", clean).strip()
    if not clean:
        return NormalizedFile(path="", dropped=True, warning="Empty file path ignored.")
    # Windows absolute or drive-qualified paths, and POSIX absolute paths.
    win_abs = re.match(r"^[A-Za-z]:[\\\\/]", clean)
    posix_abs = clean.startswith("/")
    if win_abs or posix_abs:
        return NormalizedFile(
            path="",
            dropped=True,
            warning=f"Absolute/host path '{clean}' dropped (FR-008).",
        )
    if ".." in clean:
        return NormalizedFile(
            path="",
            dropped=True,
            warning=f"Out-of-repo reference '{clean}' dropped (FR-008).",
        )
    return NormalizedFile(path=clean)


def _classify(source_task_type: str | None, title: str, desc: str) -> str:
    """Classify a task as test | implement | validate by intent (FR-013)."""
    text = f"{title} {desc}".lower()
    if source_task_type:
        return source_task_type
    if any(k in text for k in ("test", "test_suite", "mock", "fixture")):
        return "test"
    if any(k in text for k in ("validate", "review", "verify", "audit")):
        return "validate"
    return "implement"


def _extract_source_type(title: str, desc: str) -> str:
    return _classify(None, title, desc)


def parse_tasks(content: str, repo_root: str = "") -> ParseTasksResult:
    """Parse ``tasks.md`` into an ordered list of TechnicalSubtask."""
    result = ParseTasksResult()
    lines = content.splitlines()
    current_title = ""
    current_desc_parts: list[str] = []
    current_files: list[str] = []
    current_acceptance: list[str] = []
    current_state = ""
    current_tid = ""

    def flush() -> None:
        nonlocal current_tid  # noqa: SLF001
        nonlocal current_title
        nonlocal current_desc_parts
        nonlocal current_files
        nonlocal current_acceptance
        if not current_tid:
            return
        normalized = [
            normalize_file_paths([f], repo_root)
            for f in current_files
        ]
        kept = [n.path for n in normalized if not n.dropped]
        for n in normalized:
            if n.dropped and n.warning:
                result.warnings.append(n.warning)
        result.subtasks.append(
            TechnicalSubtask(
                title=current_title,
                description="\n".join(current_desc_parts),
                files=kept,
                acceptance_criteria=list(current_acceptance),
                source_task_id=current_tid,
                source_task_type=_extract_source_type(
                    current_title, "\n".join(current_desc_parts)
                ),
                completed=current_state.lower() == "x",
            )
        )
        current_tid = ""
        current_title = ""
        current_desc_parts = []
        current_files = []
        current_acceptance = []

    for line in lines:
        m = TASK_RE.match(line)
        if m:
            flush()
            current_state = m.group(1)
            current_tid = m.group(2).upper()
            current_title = m.group(3).strip() or current_tid
            # A task line's own trailing text may itself be a file reference.
            continue
        fm = FILE_RE.match(line)
        if fm:
            current_files.append(fm.group(1).strip())
            continue
        # Descriptions accumulate until the next task/file marker.
        if line.strip() and not line.strip().startswith(("#", "##", "###", "<!--")):
            current_desc_parts.append(line.strip())
    flush()

    _detect_shared_file_conflicts(result)
    return result


def _touched(subtask: TechnicalSubtask) -> set[str]:
    return {SHARED_RE.sub("/", f).lower() for f in subtask.files}


def _detect_shared_file_conflicts(result: ParseTasksResult) -> None:
    """Flag any file touched by two non-adjacent-parallel tasks."""
    for i, a in enumerate(result.subtasks):
        for b in result.subtasks[i + 1 :]:
            shared = _touched(a) & _touched(b)
            for f in shared:
                result.conflicts.append(
                    SharedFileConflict(
                        source_task_id_a=a.source_task_id,
                        source_task_id_b=b.source_task_id,
                        file=f,
                    )
                )


__all__ = [
    "NormalizedFile",
    "ParseTasksResult",
    "SharedFileConflict",
    "normalize_file_paths",
    "parse_tasks",
]
