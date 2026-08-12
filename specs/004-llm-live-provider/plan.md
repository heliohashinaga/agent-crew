# Implementation Plan: Live LLM Provider & Dual-Mode Dev-Workflow

**Branch**: `004-llm-live-provider` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-llm-live-provider/spec.md`

## Summary

Add a **real, registered, OpenAI-compatible live LLM provider** to
`ai-factory` and give the **`dev_workflow` a dual-mode execution path**. By
default the workflow stays **deterministic and offline** (roles generate
placeholder code/tests locally, cost-free, testable with no network — exactly
as today). When an operator **explicitly opts in** to live mode **and** live
credentials are present, the roles dispatch through the shared provider,
selecting a **real model per capability level** via a configurable map. The
`researcher` web scope and the `dev_workflow` role executor share **one**
provider mechanism; switching between `opencode-go` and `openrouter` is a
matter of env vars, never code edits. Portability to a VPS is preserved: the
provider uses only Python stdlib + env vars (no dependence on the pi CLI).

**Technical approach** (from research — see `research.md`): the existing
`LLMProvider` abstraction (`ai_factory.shared.llm.provider`) already defines
`complete(messages, **kwargs) -> LLMResult` and a `FakeProvider` (deterministic,
network-free). We add a concrete `OpenAICompatibleProvider` (stdlib `urllib`,
env/secret-source credentials per FR-018, secrets redacted), register it as
`openai-compatible`, and build a **dual-mode role executor** in the
`dev_workflow` that selects offline vs. live per run. `RoleAssignment.model`
already carries the nominal capability-level label; we map it to real model ids.

## Technical Context

**Language/Version**: Python ≥ 3.14, managed with `uv`. `pytest` (unit +
contract, network-free) and `-m integration` (real network/LLM, gated).

**Primary Dependencies**:
- None new for the provider — uses Python stdlib `urllib.request` (network) and
  `json`. (No openai/anthropic SDK, consistent with the repo's "no network
  deps in core" posture.)
- Existing: `ai_factory.shared.llm.provider` (`LLMProvider`, `LLMResult`,
  `LLMMessage`, `FakeProvider`, `create_provider`, `PROVIDERS` registry,
  `register_provider`), `ai_factory.shared.secrets.loader`
  (`SecretSource`, `load_credential`, `redact_secret_like`, `REDACTED`).
- `ai_factory.capability_levels` — `RoleAssignment.model` nominal labels
  (`fast-cheap`/`capable`/`deep`).
- `ai_factory.dev_workflow.graph` — `_NODE_ROLE` node→role map;
  `code_worker.worker.implement` is the offline entrypoint (deterministic).

**Storage / Credentials**:
- Only **environment variables or an injected `SecretSource`** for credentials
  (FR-018): `OPENCODE_GO_API_KEY`, `OPENROUTER_API_KEY` (and optional
  `OPENCODE_GO_BASE_URL`/`OPENROUTER_BASE_URL`). Never committed config.
- **Live opt-in**: env `AI_FACTORY_LIVE=1` (or CLI `--live`) is required **and** a
  resolvable provider key (`OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY`); either
  alone → offline (FR-009).
- Per-capability-level model map: code defaults `< optional `model-map.json` `< env
  `MODEL_FAST_CHEAP`/`MODEL_CAPABLE`/`MODEL_DEEP` (with `MODEL_DEFAULT` fallback).
  Each level resolves a provider-prefixed model id, so `opencode-go` and
  `openrouter` can be used simultaneously.

**Testing** (per constitution Principle III Red-Green and Principle IV):
- Unit/contract: `pytest` with a **stubbed transport** for the live provider
  (freeze `urllib.request.urlopen`) — no network, no cost.
- Integration: `-m integration` real HTTP/LLM, best-effort, skipped when
  unavailable (same gating as the `researcher` web scope in `003-researcher`).
- A test MUST assert that no HTTP call occurs outside `-m integration` and that
  the offline path is preserved (comes clean with the network blocked).

**Target Platform**: Any Linux/macOS host with Python ≥ 3.14 — notably a
**slim VPS with bare Python + env vars**, no pi CLI installed.

**Constraints**:
- Credentials from env/secret-store only; codebase secrets auto-redacted from
  logs/telemetry (FR-018). The provider's error strings MUST redact the API key.
- Offline is the **default and must never change**; the presence of credentials
  alone never switches a run to live. Live requires **both** `AI_FACTORY_LIVE=1`
  (or `--live`) **and** a resolvable API key.
- `dev_workflow` roles stay deterministic offline; live is a new opt-in path
  gated by flag/env.
- Cost: live is bounded by explicit opt-in; offline is always cost-free.

**Scale/Scope**: single-user, local artifacts. Model selection **per role** by
capability level (FR-010) is in scope; per-deployment model tuning via env is
in scope. Batch/selections beyond role-level are out of scope.

## Constitution Check

*GATE: must pass before implementation.*

| Principle | Status | Evidence / Plan |
|-----------|--------|-----------------|
| **I. Library-First** | ✅ PASS | Provider is a standalone lib (`ai_factory.shared.llm.openai_compatible`); dual-mode executor is a library seam consumed by the graph — libraries never depend on a workflow. |
| **II. CLI Interface** | ✅ PASS | Each role already exposes a CLI; live mode adds a `--live`/env opt-in rather than a new non-CLI path; JSON + human + exit codes preserved. |
| **III. Test-First (NON-NEGOTIABLE)** | ✅ PASS | Red-Green per task in `tasks.md`; live provider tested with stubbed transport (network-free) + `-m integration`. |
| **IV. Integration Testing** | ✅ PASS | Integration test asserts offline path identical to today with network blocked; live path exercised under `-m integration` (best-effort). |
| **V. Simplicity & Observability** | ✅ PASS | One provider, two call sites; per-role model resolution emits telemetry (role, level, model, tokens, cost, latency); YAGNI kept (role-level only). |

**Gate result**: PASS — no violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-llm-live-provider/
├── plan.md        # This file
├── research.md    # Phase 0 output
├── data-model.md  # Phase 1: entities & validation rules
├── contracts/     # Phase 1: provider + model-map contracts
├── quickstart.md  # Phase 1: runnable validation scenarios
├── spec.md        # Spec (dual-mode)
├── checklists/requirements.md
└── tasks.md       # Phase 2 task breakdown
```

### Source Code (repository root) — new/changed files

```text
src/ai_factory/
├── shared/
│   └── llm/
│       ├── provider.py                     # register_openai_compatible side effect
│       └── openai_compatible.py            # NEW OpenAICompatibleProvider
├── capability_levels/
│   └── model_map.py                        # NEW per-capability-level → real model id
└── dev_workflow/
    ├── executor/
    │   └── runner.py                       # NEW dual-mode role runner (offline/live)
    └── graph.py                            # wire dual-mode runner; derive `standard`→`capable`

(Also: `researcher/web.py` gains a path to inject the registered
`openai-compatible` provider — call site #1 (FR-007, T024).)
```

### Tests (new)

```text
tests/unit/shared/llm/test_openai_compatible.py
tests/unit/capability_levels/test_model_map.py
tests/unit/dev_workflow/executor/test_dual_mode.py
tests/unit/researcher/test_web_live_provider.py   # T024 — researcher web consumes shared provider
tests/integration/shared/llm/test_openai_compatible_live.py
```

## Complexity Tracking

This feature adds a **dual-mode execution path** to the `dev_workflow` (was
hard-offline). That is a real behavioral surface: (1) a stdlib network provider,
(2) a per-capability-level model map, and (3) an executor that switches
offline/live. Justification: the user explicitly requested roles that can run
offline **and** with a real LLM per level, while preserving the offline/testable
default. The offline path is unchanged; live is additive and opt-in. No new
complexity beyond what the dual-mode requires.
