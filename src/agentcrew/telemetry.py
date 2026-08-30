"""Offline observability: a callback handler that records LangChain run metrics.

Library-first, offline and credential-free — no LangSmith, no network. Use it
to measure per-run latency, counts, and inputs/outputs in tests or lightweight
local observability. For hosted dashboards and token/cost tracing, see
``docs/langsmith.md`` (opt-in, requires a LangSmith API key).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


@dataclass
class RunMetrics:
    """Measured metrics for a single LangChain run (chain or LLM)."""

    type: str
    input: Any
    output: Any = None
    error: str | None = None
    latency_ms: float = 0.0


class MetricsCallbackHandler(BaseCallbackHandler):
    """Offline callback handler that records per-run LangChain metrics.

    Captures chain and LLM start/end (plus error) events to measure latency,
    counts, and inputs/outputs. Pass it via run ``config``::

        node = build_hello_world_node()
        handler = MetricsCallbackHandler()
        node.invoke("Ada", config={"callbacks": [handler]})
        print(handler.avg_latency_ms())  # average chain latency (ms)
    """

    def __init__(self) -> None:
        self.runs: list[RunMetrics] = []
        self.errors: list[RunMetrics] = []
        self._started: dict[str, tuple[float, str, Any]] = {}

    def _start(self, run_id: str, kind: str, inputs: Any) -> None:
        self._started[run_id] = (time.perf_counter(), kind, inputs)

    def _finish(self, run_id: str, output: Any, *, is_error: bool = False) -> None:
        started = self._started.pop(run_id, None)
        if started is None:
            return
        t0, kind, inputs = started
        metrics = RunMetrics(
            type=kind,
            input=inputs,
            output=None if is_error else output,
            error=str(output) if is_error else None,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )
        self.runs.append(metrics)
        if is_error:
            self.errors.append(metrics)

    # --- chains ---
    def on_chain_start(
        self, serialized: dict, inputs: Any, *, run_id: str, **kwargs
    ) -> None:
        self._start(str(run_id), "chain", inputs)

    def on_chain_end(self, output: Any, *, run_id: str, **kwargs) -> None:
        self._finish(str(run_id), output)

    def on_chain_error(self, error: BaseException, *, run_id: str, **kwargs) -> None:
        self._finish(str(run_id), error, is_error=True)

    # --- LLMs ---
    def on_llm_start(
        self, serialized: dict, prompts: list[str], *, run_id: str, **kwargs
    ) -> None:
        self._start(str(run_id), "llm", prompts)

    def on_llm_end(self, response: Any, *, run_id: str, **kwargs) -> None:
        self._finish(str(run_id), getattr(response, "generations", response))

    def on_llm_error(self, error: BaseException, *, run_id: str, **kwargs) -> None:
        self._finish(str(run_id), error, is_error=True)

    # --- stats helpers ---
    def count_runs(self) -> int:
        return len(self.runs)

    def avg_latency_ms(self) -> float | None:
        values = [m.latency_ms for m in self.runs]
        return (sum(values) / len(values)) if values else None