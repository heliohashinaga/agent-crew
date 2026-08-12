# Contracts — Live LLM Provider & Dual-Mode Dev-Workflow (004)

This feature exposes **two** contracts:

1. **OpenAI-compatible live provider** (`openai-compatible`) — a library
   contract implementing `LLMProvider`; configured via env vars, portable to a
   VPS. See [openai-compatible-provider.md](./openai-compatible-provider.md).
2. **Per-role capability-level model map** — resolves a **role + a capability
   level** to a real, provider-prefixed model id, via `model-map.json` +
   env overrides. See [model-map.md](./model-map.md).

Both are consumed by the two call sites (the `researcher` web scope and the
`dev_workflow` role executor). There is **no new CLI in this feature**: the
live-mode opt-in is via the existing role CLIs (env `AI_FACTORY_LIVE=1` or
`--live`), preserving the JSON + human + exit-code contract each role already
exposes.
