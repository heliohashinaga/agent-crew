# Contract: `Actor` / `Gate` Seams (Loop Engineering)

`loop_engine` is a **reusable harness over two injectable seams**: the `Actor`
(what produces work each iteration) and the `Gate` (what verifies it). The core
loop logic depends only on these interfaces; `FakeActor`/`FakeGate` make it
deterministic and network-free in tests, and concrete bindings (Q1=A, Q2=C) plug
into the same seams in production.

This contract defines the seam interfaces and the test fakes.

## The `Actor` seam

```python
class Actor(Protocol):
    def invoke(self, context: RepairContext) -> ActorOutput: ...
```

- **`context: RepairContext`** — carries the previous gate failure verdict
  (bounded, concise — never a full dump) and the run's accumulated repair
  context (FR-006). For the first iteration, `context` is empty/no prior failure.
- **`ActorOutput`** — `status: bool` (did the actor *report* success? this is
  **not** the loop's verdict), `artifact_refs: list[str]`, `description: str`,
  `summary: str`.

**No self-grading (FR-002, US2)**: the actor's `status` claim is never used to
decide `passed`. Only the external `Gate` decides. A `FakeActor` that always
claims success while the `FakeGate` fails must yield `exhausted` (not `passed`),
with the held-back reason being the gate's, not the actor's.

## The `Gate` seam

```python
class Gate(Protocol):
    def verify(self, artifact: Any) -> GateVerdict: ...
```

- **`GateVerdict`** — `passed: bool`, `checks: list[CheckResult]`, `consumed:
  BudgetDelta`. `passed` is `true` only if **all** configured checks pass
  (aggregate, Q2=C); per-check breakdown drives both the outcome and the repair
  path.
- **`CheckResult`** — `name`, `stage` (`deterministic` | `reviewer`), `passed`,
  `reasons` (bounded), `consumed`.
- A gate that errors/unavailable **raises a typed error** (never a silent pass).

## Two-stage gate (Q2=C, FR-011)

`CompositeGate` runs:
1. **Deterministic checks** first — network-free (e.g. `suite_pass`,
   `contract_pass` on the produced artifact). MUST pass before stage 2.
2. **Independent reviewer** — a separate role/model reviewing the artifact.
   Runs only after stage 1 passes. Integration-gated (`-m integration`); when
   network/LLM is unavailable it surfaces clearly (typed error or documented
   skip, explicit), **never a silent pass**.

The deterministic core remains network-free even when the composite gate is
review-aware — exactly the `researcher` `repo` vs `web` scoping split.

## Concrete binding (Q1=A)

`FactoryActor` over the factory's folder-driven dev pipeline (approved spec
folder → orchestrated execution → result). **Library-only seam in v1**: it is
not wired into `dev_workflow` nodes (FR-010). Future actors (media/video,
arbitrary tasks) bind to the same `Actor` interface without changing the core
(FR-012).

## Test fakes (deterministic, network-free)

- **`FakeActor`** — a scripted `Actor`: configurable outputs per call
  (success/failure, artifact refs, summaries), optionally reading the repair
  `context` to prove repair propagation.
- **`FakeGate`** — a scripted `Gate`: configurable verdict sequence (pass on 1st
  call, pass on k+1th, never pass) and structured `reasons`, optionally a
  raising variant for the "gate unavailable" case.

These fakes let every US1–US3 determinism test (iteration counts,
repair-context propagation, no-self-grading, termination) run with **no
network** (SC-001, SC-002, SC-003).