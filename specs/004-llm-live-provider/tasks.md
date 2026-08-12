# Tasks: Live LLM Provider & Dual-Mode Dev-Workflow

> `004-llm-live-provider`
> Status: Planned

- [ ] **Constitution**: TDD is non-negotiable — every implementation task starts
      from a failing (Red) test. No code merges without passing tests. Ruff must
      pass (`uv run ruff check .`). `pytest` (unit + contract) must pass with no
      network required; real-LLM tests are gated `-m integration`.
- [ ] Implementation order: Phase 1 (provider, US1/US2) → Phase 2 (model map,
      FR-010) → Phase 3 (dual-mode executor + researcher web wiring, US3/US4 +
      FR-007/FR-009) → Phase 4 (offline-preservation tests + green suite)
      → Phase 5 (integration + docs).

## Phase 1 — OpenAI-Compatible Live Provider (US1/US2)

> Delivers the portable stdlib provider, registered, offline-safe, redacting
> secrets. This is the "configure models via env vars" surface.

### User Story 1 - Query the Web with a Real LLM (web scope); User Story 2 - Configure via Env

- [x] **T001 — Specify & approve** — Author this feature's `spec.md`, `plan.md`,
      `research.md`, and `tasks.md`. Approved by the user before implementation.
      *(DONE — artifacts exist and approved; not a code task.)*
- [ ] **T002 — Scaffold `openai_compatible` package [Red→Green]** — Add
      `src/ai_factory/shared/llm/openai_compatible.py` with empty
      `OpenAICompatibleProvider` class + module imports only. **Red**: a smoke
      test importing `ai_factory.shared.llm.openai_compatible` fails to collect.
- [ ] **T003 — `OpenAICompatibleProvider` registered & buildable [Red→Green]** —
      Register the provider as `openai-compatible` in the `PROVIDERS` registry so
      `create_provider("openai-compatible")` returns an instance (and an unknown
      name still raises the existing typed error). Constructor performs **no
      network I/O** and is always safe to build with no env vars (documented
      default `base_url`/`model`). **Red**: unit test asserts registration +
      `create_provider("openai-compatible")` works and unknown names still raise.
- [ ] **T004 — Resolve creds from SecretSource/env, never commit [Red→Green]** —
      The provider reads `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`,
      `OPENAI_COMPATIBLE_MODEL` via `load_credential`/injected `SecretSource`
      (FR-018); a missing API key fails fast with a clear typed error. **Red**:
      unit test injects a `_StubSecretSource` and asserts resolution; a missing key
      raises a typed, clear error with no hang.
- [ ] **T005 — `complete()` posts `/v1/chat/completions` & parses `LLMResult`
      [Red→Green]** — `complete(messages, **kwargs)` builds an OpenAI-compatible
      body (`model`, `messages`, optional `temperature`/`max_tokens`), POSTs to
      `<base_url>/chat/completions`, and parses `choices[0].message.content`,
      `usage`, `model` into an `LLMResult`. Uses stdlib `urllib.request` only.
      **Red**: unit test **freezes `urllib.request.urlopen`** with a canned
      OpenAI-compatible JSON response and asserts the returned `LLMResult`
      (content/model/tokens_in/tokens_out) and that the request body carried the
      right model + messages. No network touched.
- [ ] **T006 — Per-call model/temperature/max_tokens overrides [Red→Green]** —
      `kwargs` override `model`, `temperature`, `max_tokens`, defaulting to
      provider-configured values — so an operator can switch models per call
      (e.g. cheap rank/summarize vs. capable) without code changes. **Red**: unit
      test asserts the request body reflects per-call overrides.
- [ ] **T007 — Error typing + secret redaction [Red→Green]** — Non-2xx status and
      non-JSON responses raise the concrete **`OpenAICompatibleError`** (in
      `openai_compatible.py`) whose message **redacts the API key** (reuse
      `redact_secret_like`/`REDACTED` from `secrets.loader`, FR-018). **Red**: unit
      test asserts an HTTP error containing the key in the body surfaces
      `OpenAICompatibleError` with `[REDACTED]` and no leaked key.

## Phase 2 — Per-Capability-Level Model Map (FR-010)

> Maps the nominal `RoleAssignment.model` labels (`fast-cheap`/`capable`/`deep`)
> to real model ids, env-overridable. Reused by the dual-mode executor.

### User Story 4 (supporting) - Resolve model id per capability level

- [ ] **T010 — `model_map.py` with defaults + env override [Red→Green]** — Add
      `src/ai_factory/capability_levels/model_map.py`: a function
      `resolve_model_id(level: str) -> str` returning a documented default real
      model id for `fast-cheap`/`capable`/`deep`, overridable via env (named
      `AI_FACTORY_MODEL_FAST_CHEAP`/`AI_FACTORY_MODEL_CAPABLE`/`AI_FACTORY_MODEL_DEEP`,
      with `AI_FACTORY_MODEL_DEFAULT` fallback). Unknown level falls back to the
      documented default. Defaults target the `opencode-go` OpenAI-compatible
      model ids when `OPENAI_COMPATIBLE_BASE_URL` points at opencode-go. **Red**:
      unit tests assert defaults, env override, and unknown-level fallback.

## Phase 3 — Dual-Mode Role Executor (US3/US4, FR-009)

> The core behavioral change: the `dev_workflow` runs offline by default and can
> opt into live per run. Reuses `RoleAssignment.model` (existing schema).

### User Story 3 - Offline by default; User Story 4 - Run roles offline or with a real LLM

- [ ] **T020 — `runner.py` dual-mode switch [Red→Green]** — Add
      `src/ai_factory/dev_workflow/executor/runner.py`: a role runner with two
      modes. **Offline** (default): delegate to the current deterministic
      functions (e.g. `code_worker.worker.implement`) — behavior **identical to
      today**, no network, no creds required. **Live** (opt-in `AI_FACTORY_LIVE=1`
      / `--live`): resolve the role's real model id (via
      `model_map.resolve_model_id` on its `RoleAssignment.capability_level`) and
      dispatch through the registered provider. **Red**: unit test — offline mode
      with network blocked produces the same deterministic output; live mode with a
      **stubbed transport** calls `provider.complete` with the correct model id.
- [ ] **T021 — Opt-in gate: creds alone never go live [Red→Green]** — A run goes
      live **only** when `AI_FACTORY_LIVE=1`/`--live` **and** a live API key are
      both present; otherwise (even with creds set) it runs offline. **Red**: unit
      test asserts (creds, no opt-in) → offline; (opt-in, no creds) → offline;
      (opt-in + creds) → live.
- [ ] **T022 — Fail-closed on unresolvable model id [Red→Green]** — If a live role's
      capability level has no mapped real model id, the role **fails closed** (stays
      on the deterministic path or raises a typed, actionable error) — never calls
      the provider with an empty/garbage model id. **Red**: unit test asserts
      fail-closed behavior (Edge Case).
- [ ] **T023 — Wire dual-mode into the graph [Red→Green]** — Update
      `src/ai_factory/dev_workflow/graph.py` to use the dual-mode runner instead of
      directly calling each deterministic function. **Required pre-step**: the graph
      hardcodes `capability_level="standard"` (line ~147), which is **not one of**
      the model-map domain labels (`fast-cheap`/`capable`/`deep`). Decide a mapping
      for `standard` → `capable` (documented) so live mode resolves a real model, and
      update the graph to derive the level from `RoleAssignment` where possible.
      **Red**: graph smoke test — offline run follows the deterministic path;
      live run (stubbed) dispatches via provider with the resolved model id.
- [ ] **T024 — Wire the shared provider into the `researcher` web scope
      [Red→Green] (call site #1 / FR-007)** — The `researcher` web scope already
      takes an injected `LLMProvider` (Option D); add/confirm a path that injects
      the registered `openai-compatible` provider (via `create_provider` / env
      creds) so a `web`-scope lookup can use the live model without code edits.
      Offline default is unchanged: without creds it still uses `FakeProvider`.
      **Red**: unit test — a `web`-scope lookup injected with a stubbed transport
      `openai-compatible` provider returns an `LLMResult`-summarized result with no
      network; without creds it falls back to `FakeProvider` (US1/scenario 2).

## Phase 4 — Offline-Preservation & Green Suite

> Prove the default never breaks and the whole suite stays network-free.

- [ ] **T030 — Offline suite runs with network blocked [Red→Green]** — A test
      blocks HTTP (freeze `urllib.request.urlopen` to raise if called) and asserts
      the full unit/contract path completes with no network and results identical
      to baseline. **Red**: test fails if any deterministic role touches HTTP.
- [ ] **T031 — Telemetry invariants [Green]** — Live-mode emissions record role,
      capability level, resolved model id, tokens, cost, latency; no API key in
      any telemetry/log (reuse redaction, FR-018/SC-005).
- [ ] **T032 — Whole-suite green gate (offline) [Green]** — `uv run ruff check .`
      passes; `pytest` unit+contract green with no network required. (Separate from
      telemetry invariants so each is verifiable independently.)

## Phase 5 — Integration & Docs

> Real network/LLM, gated `-m integration`, best-effort.

- [ ] **T040 — Live integration path [Red→Green]** — Under `-m integration`, run
      the live provider against a real endpoint when `OPENAI_COMPATIBLE_*` are set,
      and the `web` scope end-to-end; skip gracefully when network/creds
      unavailable (customary best-effort gate). **Red**: integration test under
      `tests/integration/...` that is skipped without creds/network.
- [ ] **T041 — Docs & quickstart [Green]** — Document the env-vars config surface
      (how to point at `opencode-go` vs `openrouter`), the per-capability-level
      model map + overrides, and the offline-vs-live opt-in; update
      `specs/004-llm-live-provider/quickstart.md`. Final green: `uv run ruff check .`
      + `uv run pytest` (unit+contract, no network) + best-effort `-m integration`.

## Acceptance Handoff

Pass criteria:
- [ ] `create_provider("openai-compatible")` returns a working stdlib provider;
      unknown names still raise (SC-001).
- [ ] Default `dev_workflow` (no opt-in) is **offline**: unit+contract suite
      passes with the network blocked and no HTTP call outside `-m integration`
      (SC-002, SC-006).
- [ ] Live mode (`AI_FACTORY_LIVE=1` + creds + stubbed transport, or the
      researcher web scope injected with a stubbed `openai-compatible` provider)
      calls the provider with the **model id mapped from the role's capability
      level** and returns consistent products (SC-007, FR-007 call sites #1/#2).
- [ ] Configuring models is env-var-only (opencode-go vs openrouter by base_url/
      model/api_key); no committed config (SC-003).
- [ ] No secret is emitted in any error/log/telemetry (SC-005).
- [ ] `uv run ruff check .` and `uv run pytest` (unit+contract, network-free) pass;
      `-m integration` is best-effort gated (SC-004).
- [ ] The `researcher` web scope can consume the shared `openai-compatible` provider
      without code edits (via `create_provider` / env) and falls back to
      `FakeProvider` without creds (T024 / US1-scenario 2 / FR-007 call site #1).
