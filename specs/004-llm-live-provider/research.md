# Research: Live LLM Provider & Dual-Mode Dev-Workflow

**Feature**: `004-llm-live-provider` | **Date**: 2026-08-12

## Decision Context

The user wants the `dev_workflow` to run **offline by default** (roles
deterministic, cost-free, testable with no network) **and** be able to run with
a **real LLM** per capability level, optionally. Requirement: portable to a VPS,
configurable via env vars, no dependence on the pi CLI, and offline preserved.

## Findings

- `ai_factory.shared.llm.provider` already defines `LLMProvider` ABC,
  `LLMResult`, `LLMMessage`, `FakeProvider` (deterministic/network-free), a
  `PROVIDERS` registry, `create_provider`, and `register_provider` (T012/R5,
  FR-018). The seam exists and is used by `researcher/web.py`.
- `RoleAssignment` (in `dev_workflow/models.py`) already carries `model`,
  `capability_level`, budget, timeout, etc. So per-role model data **already
  exists**; only the execution wiring is missing — no data-model change needed.
  each (role, level) pair resolves to a real model id; task levels are
  `simple`/`standard`/`complex`, review levels `shallow`/`standard`/`deep`
  (`capability_levels`).
- `graph.py` currently hardcodes `capability_level="standard"` (line ~147) and
  dispatches roles via CLI wrappers (`code_worker/cli.py`,
  `code_reviewer/cli.py`, etc.); `code_worker.worker.implement` is the current
  offline entrypoint (deterministic, generates placeholder + tests, `py_compile`).
- No third-party HTTP client is declared in `pyproject.toml` (no openai/
  anthropic/httpx/requests). Core LLM calls must go through stdlib `urllib` or
  an injected `LLMProvider` — consistent with offline-first posture.

## Design Choices

1. **One provider, two call sites**: a single `OpenAICompatibleProvider`
   (stdlib `urllib`, `POST /v1/chat/completions`) serves both the `researcher`
   web scope and the `dev_workflow` role executor. Default = `FakeProvider`.
2. **Offline-by-default preserved**: `dev_workflow` runs the deterministic path
   unless both an explicit opt-in (flag/env) and live credentials are present.
   Presence of creds alone never changes behavior.
3. **Per-role capability-level model map** (`capability_levels/model_map.py`): maps
   each (role, level) pair to a real, provider-prefixed model id via
   code defaults `< model-map.json` `< env. Executor resolves the id per role in
   live mode.
4. **Dual-mode runner** (`dev_workflow/executor/runner.py`): offline delegates to
   current deterministic functions; live dispatches through the provider.
5. **Credentials**: env/secret-store only (FR-018); error/telemetry strings
   redact the API key (reuse `redact_secret_like`/`REDACTED`).
6. **Green gating**: live provider tested with a stubbed `urllib` transport
   (network-free); real HTTP/LLM under `-m integration`, best-effort.

## Portability (VPS)

Provider + map + runner use only Python stdlib and env vars → run on a slim VPS
with Python ≥ 3.14 and no pi CLI installed. Both providers (opencode-go and
openrouter) can run simultaneously; each capability level selects its provider
via a provider-prefixed model id (API keys via `OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY`).

## Open Investigation (todo in T023)

`graph.py` hardcodes `capability_level="standard"`; verify the dual-mode runner
derives the true level from `RoleAssignment` so live mode resolves the correct
model id per role.
