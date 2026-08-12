# Feature Specification: Live LLM Provider for Researcher & Dev-Workflow Roles (dual-mode)

**Feature Branch**: `004-llm-live-provider`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User decision — **dual-mode**: the `dev-workflow` must keep running **offline by default** (roles deterministic, cost-free, for testing) while **also being able to run with real LLM** per role by level of capability. The live LLM talks through an OpenAI-compatible provider using environment credentials; switching between `opencode-go` and `openrouter` happens by env vars, not code edits. The live provider must be portable to a VPS (bare Python + env vars, no dependence on the pi CLI).

## Scope Statement

This feature adds a **real, registered, OpenAI-compatible live LLM provider** to `ai-factory` (powering the `researcher` web scope) **and** gives the **`dev_workflow` a dual-mode execution path**: by default the roles stay **deterministic and offline** (the current `implement`-style pipeline, cost-free, testable with no network); when live credentials are present, the relevant roles dispatch through the real provider using the model mapped to their capability level.

**The off-line mode is the default and never changes**: even with env credentials set, the workflow keeps its deterministic path unless a run explicitly opts in to the live mode (per-run flag / env). The `researcher` web scope and the `dev_workflow` role executor both consume the **same registered `openai-compatible` provider** — one mechanism, two call sites. Portability to a VPS stays intact: the provider uses only Python stdlib + env vars.

## Clarifications

- Q: Where does the live LLM live? → A: In **two call sites** through one provider: the `researcher` web scope **(Option C baseline)** **and** the `dev_workflow` role executor (this expansion). The `dev_workflow` gains a **dual-mode**: offline by default, opt-in live per role.
- Q: Does live mode change the offline behavior? → A: **No.** Offline is the default and never changes. Live only activates when a run **explicitly opts in** AND live credentials are present; otherwise the deterministic path runs exactly as today.
- Q: How is live mode opted into? → A: By setting the env var **`AI_FACTORY_LIVE=1`** (or passing `--live` at the CLI, which sets the same). **Precedence**: a run is live **only** if both `AI_FACTORY_LIVE=1`/`--live` is set **AND** a live API key is resolvable (`OPENAI_COMPATIBLE_API_KEY` present). Presence of **either** alone → offline. No hidden auto-detect: creds alone never trigger live.
- Q: What provider protocol does the live provider speak? → A: An **OpenAI-compatible `POST /v1/chat/completions`** contract (shared by both opencode-go and openrouter). The provider is a standard library implementation with **no third-party HTTP dependency** (uses Python stdlib `urllib`), so it runs portably on a VPS with only Python + env vars.
- Q: How are credentials supplied? → A: **Environment variables only** (or an injected secret source), per FR-018. The factory never embeds keys in committed config. Live is opt-in: `FakeProvider` remains the default when no credentials are set.
- Q: How does a run stay offline/cost-free in tests? → A: The default stays `FakeProvider`. The live provider is exercised via stubbed HTTP in unit tests (no network) and gated `-m integration` for real calls. A unit/contract test asserts the suite does not touch the network.
- Q: How is the model chosen **per role** in the `dev_workflow`? → A: Each `RoleAssignment.model` nominal label (`fast-cheap`/`capable`/`deep`, from `capability_levels`) is mapped to a real model id by a **per-capability-level model map** (config/env). In live mode the executor reads `RoleAssignment.model`'s level → maps it to the real id → calls the provider. Still configurable via env vars; no code edit for opencode-go vs openrouter.
- Q: How is the model chosen in the `researcher` web scope? → A: Via env vars (`OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_MODEL`) and/or per-call override.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query the Web with a Real LLM (Priority: P1)

An operator has configured the researcher with live credentials (e.g. opencode-go or openrouter) and runs a `web`-scope query (`ai-factory-researcher --scope web ...` or a `lookup(..., scope="web")` inside the factory). The researcher runs its multi-angle queries, ranks candidates by quality, fetches content, and summarizes — all through a **real hosted model** — returning a concise `ResearchResult` with URL sources and a synthesized summary.

**Why this priority**: The web scope is a primary consumer of the shared live provider — it calls a real hosted model for ranking and summarization. Combined with the `dev_workflow` dual-mode, this is where a live model is actually used; everything else stays offline.

**Independent Test**: At the library layer, inject a stubbed transport that returns a canned OpenAI-compatible JSON response and assert `provider.complete(...)` returns an `LLMResult` with the expected `content`, `model`, and `tokens_in`/`tokens_out` — **without network**. The real network/LLM path is exercised under `-m integration` (gated, best-effort, skipped unavailable).

**Acceptance Scenarios**:

1. **Given** credentials present and a `web`-scope lookup with real fetchers, **When** it runs under `-m integration`, **Then** it returns a `ResearchResult` with URL `sources` and an LLM-summarized `summary` (HTTP+LLM best-effort; skipped when network unavailable).
2. **Given** no credentials, **When** a `web`-scope lookup runs, **Then** it falls back to `FakeProvider` (no network, no cost), never a silent hang or secret leak. (A missing API key only raises a typed error when live mode is explicitly requested.)
3. **Given** the unit test suite, **When** tests run without `-m integration`, **Then** no network is touched (asserted) and all deterministic tests pass.

---

### User Story 2 - Configure Models by Env Vars (Priority: P1)

An operator configures the live provider without editing any code: they export `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, and `OPENAI_COMPATIBLE_MODEL` (or run `register_provider`/inject a configured instance), and the researcher web scope begins using that model.

**Why this priority**: The user explicitly asked "como configuro os modelos usados pelos agents" — with this feature the answer is "export env vars", portable to a VPS with bare Python.

**Independent Test**: Can be tested by constructing the provider with an injected `SecretSource` and asserting it resolves `base_url`/`api_key`/`model` from it (no committed config), and that `create_provider("openai-compatible")` returns a usable provider registered under a stable name.

**Acceptance Scenarios**:

1. **Given** a `SecretSource`/env supplying base_url+api_key+model, **When** an `openai-compatible` provider is created/viewed, **Then** it uses those values (and documents a default base_url/model when absent).
2. **Given** an unknown provider name, **When** `create_provider` runs, **Then** it raises the existing typed `UnknownProviderError`.
3. **Given** a run without env credentials, **When** the default is requested, **Then** `FakeProvider` is used (no network, no cost).

---

### User Story 3 - Keep the Dev Workflow Offline by Default (Priority: P1)

The factory's Development Workflow must remain fully deterministic and network-free **by default** regardless of whether live LLM credentials are present. Live LLM is confined to the shared provider and only activates with **explicit opt-in**.

**Why this priority**: This is the user's explicit requirement — "continuar offline para poder testar sem gasto" — and the project's Library-First / determinism non-negotiables. Adding a live provider must never drag the core workflow online.

**Independent Test**: Run the full unit+contract `pytest` (no `-m integration`) with a **blocked network** (e.g. monkeypatched `urlopen` that raises if called) and assert every deterministic test passes and web-scope live calls only happen under `-m integration`.

**Acceptance Scenarios**:

1. **Given** network blocked, **When** the unit+contract suite runs, **Then** all tests pass and no live provider performs an HTTP call.
2. **Given** live credentials present but live mode **not** opted-in, **When** `dev_workflow` roles execute, **Then** they continue to use deterministic/fake paths — the presence of credentials alone does not change their behavior (same invariant as US4/scenario 3).
3. **Given** the web-scope real path, **When** it runs, **Then** it is gated `-m integration` and clearly documented as opt-in.

### User Story 4 - Run Roles Offline or with a Real LLM (dual-mode) (Priority: P1)

An operator runs the `dev_workflow` (e.g. `dev-run`) **without** live creds → the roles execute exactly as today: deterministic, network-free, cost-free (this is the default and must never break). When an operator opts in to live mode (per-run flag/env) and creds are present, the role executor dispatches each role through the registered `openai-compatible` provider, selecting the model by the role's capability level (from the `RoleAssignment.model` nominal label mapped to a real id).

**Why this priority**: The user wants roles that can run offline **and** with a real LLM per capability level, without breaking the offline/testable default.

**Independent Test**: Assert (network blocked, live off) that a role produces the identical deterministic output as today. Then assert (stubbed transport) that in live mode the same role calls `provider.complete` with the model mapped from its capability level and returns an `LLMResult`-derived product.

**Acceptance Scenarios**:

1. **Given** offline mode (default), **When** the workflow runs with the network blocked, **Then** all roles complete deterministically, no HTTP call is made, and no live creds are required.
2. **Given** live mode opted-in + creds present + stubbed transport, **When** a role runs, **Then** it calls the provider with the **real model id mapped from its capability level** and returns a product consistent with that response.
3. **Given** live mode not opted-in, **When** roles run, **Then** they use the deterministic path even if creds are present — the presence of creds alone never changes behavior.
4. **Given** a role's capability level, **When** the model map is consulted, **Then** it resolves to a real model id (e.g. `fast-cheap`→flash, `capable`→pro, `deep`→best), overridable via env, with a documented default.

### Edge Cases

- What if `OPENAI_COMPATIBLE_API_KEY` is set but `OPENAI_COMPATIBLE_BASE_URL` is not, for a provider without the default base-url? Use a documented default base URL (OpenRouter-compatible) when none is supplied; operators targeting opencode-go set the base URL explicitly.
- What if the remote server returns a non-2xx status or non-JSON body? Raise **`OpenAICompatibleError`** whose message **does not leak the API key** (FR-018 redaction via `redact_secret_like`).
- What if the live provider is requested with no API key? Fail fast with **`OpenAICompatibleError`** (or fall back to `FakeProvider` where the caller tolerates it) — never a silent hang.
- What if the model id is invalid/unavailable on the provider? Surface the provider's error as an **`OpenAICompatibleError`** (redacted), letting the operator fix the env var.
- What if an operator opts into live mode but a role's capability level has no mapped real model? Fail closed: keep that role on the deterministic path (or raise a clear, actionable error) rather than calling the provider with an empty/garbage id.
- What if a run opts into live mode but one role fails while others succeed? Each role handles its own typed error; a failing live role falls back or raises per the existing retry/escalation policy (FR-014/015), never silently dropping or leaking secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a registered `LLMProvider` implementation named `openai-compatible` that speaks an OpenAI-compatible `POST /v1/chat/completions` contract, buildable via `create_provider("openai-compatible")` and through `register_provider`. The provider MUST use **only Python stdlib** (`urllib`) — no third-party HTTP dependency — so it runs on a bare VPS with Python + env vars.
- **FR-002**: The provider MUST resolve its `api_key`, `base_url`, and `model` from an injected `SecretSource` / the environment (FR-018), with **never-committed** config. Sensible documented defaults apply for `base_url` and `model` when absent; a missing API key must fail fast (typed, clear error) rather than hang or silently misbehave.
- **FR-003**: The provider's `complete(messages, **kwargs)` MUST return an `LLMResult` with `content`, `model`, `tokens_in`, `tokens_out` parsed from the standard OpenAI-compatible response (`choices[0].message.content`, `usage`, `model`), conforming to the existing `LLMProvider` contract (T012 / R5).
- **FR-004**: Per-call overrides MUST be supported for `model`, `max_tokens`, and `temperature` via `kwargs`, defaulting to the provider-configured values — so an operator can switch models per invocation (e.g. cheap rank/summarize vs. capable) without code changes.
- **FR-005**: The provider MUST be **offline-safe by default**: constructing it performs **no network I/O**, and it performs one HTTP call only when `complete` is invoked. The canonical default remains `FakeProvider`; a run without credentials never touches the network.
- **FR-006**: Any HTTP error or malformed response MUST surface as **`OpenAICompatibleError`** (typed, wrapping the request/response failure) whose message **redacts the API key** (FR-018) via `redact_secret_like`. It MUST never leak a secret value into logs/telemetry.
- **FR-007**: System MUST confine live LLM to a **shared registered provider** used by two call sites: the `researcher` web scope **and** the `dev_workflow` role executor. The `dev_workflow` MUST keep a deterministic/offline default that is **never** changed by the presence of credentials (governing invariant — see FR-005).
- **FR-008**: The unit/contract test suite MUST run **without network** for the deterministic paths: the live provider is tested with a **stubbed transport** (canned OpenAI-compatible JSON) and gated `-m integration` for real calls. A test MUST assert that HTTP is not attempted outside `-m integration`.
- **FR-009 (dual-mode executor)**: The `dev_workflow` MUST support **two execution modes** per run: `offline` (default — roles run deterministically/network-free exactly as today) and `live` (roles dispatch through the registered provider). A run goes live **only** when `AI_FACTORY_LIVE=1`/`--live` is set **AND** a live API key is resolvable; otherwise it runs offline.
- **FR-010 (per-capability-level model map)**: The system MUST map each capability-level nominal label (`fast-cheap`, `capable`, `deep`) to a **real model id** via a configurable, env-overridable map with documented defaults: `AI_FACTORY_MODEL_FAST_CHEAP`, `AI_FACTORY_MODEL_CAPABLE`, `AI_FACTORY_MODEL_DEEP` (and a `_DEFAULT` fallback). Default ids resolve to the opencode-go openai-compatible ids when `OPENAI_COMPATIBLE_BASE_URL` points at opencode-go; operators override via env (or base_url swap to openrouter).

### Key Entities *(include if feature involves data)*

- **`OpenAICompatibleProvider`** — an `LLMProvider` implementation (OpenAI-compatible /v1/chat/completions), stdlib-only, env/secret-source credentials, offline-safe construction.
- **`LLMProvider` / `LLMResult` / `LLMMessage`** — the existing provider contract (`ai_factory.shared.llm.provider`) that every live provider implements; `FakeProvider` remains the deterministic default.
- **Env vars (credentials / configuration)**: `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_MODEL` — the "configure models" surface; portable to a VPS via `export`.
- **`researcher` web scope** — one consumer of the live provider (existing `lookup(..., scope="web")` seam, Option D, injected `LLMProvider`).
- **`dev_workflow` role executor (dual-mode)** — the second consumer: dispatches roles either deterministically (offline, default) or through the provider (live, opt-in), resolving the model id from the role's capability level via a configurable map.
- **Per-capability-level model map** — configurable (env-overridable) mapping of nominal labels (`fast-cheap`/`capable`/`deep`) to real model ids.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `create_provider("openai-compatible")` returns a working provider, and a `complete` call with a stubbed transport returns a correctly parsed `LLMResult` (content/model/tokens) — asserted in deterministic unit tests with **no network**.
- **SC-002**: The default run with no credentials uses `FakeProvider` and never touches the network; the unit+contract suite passes with the network blocked, and no live HTTP call happens outside `-m integration`.
- **SC-003**: An operator configures models using only env vars (or an injected secret source) — no committed config — and can switch between `opencode-go` and `openrouter` by changing `OPENAI_COMPATIBLE_BASE_URL`/`_MODEL`/`_API_KEY`.
- **SC-004**: All unit+contract `pytest` pass deterministically; real HTTP/LLM web-scope tests run only under `-m integration` (best-effort, skipped when unavailable). `uv run ruff check .` passes.
- **SC-005**: No secret value (API key) is emitted in any error, log, or telemetry string (FR-018 redaction asserted in a test).
- **SC-006**: The `dev_workflow` runs **offline by default**: with the network blocked and live not opted-in, all roles produce identical deterministic output to today, and no HTTP call occurs — even if creds are set.
- **SC-007**: In live mode (`AI_FACTORY_LIVE=1` + creds + stubbed transport), each role resolves its capability level to a real model id via the model map and calls the provider once with that id; products are consistent with the `LLMResult` returned.

## Assumptions

- **Dual-mode confirmed**: the user wants the `dev_workflow` to keep the deterministic/offline default **and** be able to run roles with a real LLM per capability level. Offline is default; live is explicit opt-in + creds.
- **OpenAI-compatible protocol**: opencode-go and openrouter both expose a `/v1/chat/completions` compatible surface, so a single stdlib provider serves both; providers/targets differ only by credentials (base_url/api_key/model env vars).
- **Offline-safe by default**: default remains `FakeProvider`; live only activates with credentials present **and** explicit opt-in. Unit tests stub the transport; real calls are `-m integration`.
- **Portability to VPS**: the provider uses only Python stdlib and env vars, so it runs on a slim VPS without the pi CLI or third-party HTTP client libraries.
- **Per-capability-level model map**: nominal labels (`fast-cheap`/`capable`/`deep`) map to real ids via a configurable env-overridable map with documented defaults; operators can tune it per deployment.
