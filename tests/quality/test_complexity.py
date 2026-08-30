"""Quality gate: cyclomatic complexity must stay within budget.

Runs in the deterministic CI suite (it is fast). Guards Constitution V
(Simplicity): any function growing beyond the budget must be refactored before
the change can proceed.
"""

from pathlib import Path

import pytest
from radon.complexity import cc_visit

pytestmark = pytest.mark.quality

# Upper bound = radon grade B (6-10). Grade C and above is rejected. The current
# worst offender is cli.main() at 9; raising future complexity past 10 should
# require a refactor, not just a raised limit.
MAX_COMPLEXITY = 10

SRC = Path(__file__).resolve().parents[2] / "src" / "agentcrew"


def _complexity_scores() -> dict[tuple[str, str], int]:
    scores: dict[tuple[str, str], int] = {}
    for py_file in sorted(SRC.rglob("*.py")):
        rel = py_file.relative_to(SRC.parent)
        for block in cc_visit(py_file.read_text(encoding="utf-8")):
            scores[(str(rel), block.name)] = block.complexity
    return scores


def test_max_cyclomatic_complexity():
    scores = _complexity_scores()
    assert scores, "no source files found to measure under src/agentcrew/"
    (path, name), value = max(scores.items(), key=lambda item: item[1])
    assert value <= MAX_COMPLEXITY, (
        f"{path}::{name} has cyclomatic complexity {value}, exceeding the "
        f"budget of {MAX_COMPLEXITY}. Refactor it to reduce complexity "
        f"(Constitution V: Simplicity)."
    )