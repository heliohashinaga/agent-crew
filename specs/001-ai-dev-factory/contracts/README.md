# Contracts

This directory documents the interface contracts the factory exposes and
consumes. Per the constitution (Principle II — CLI Interface), every library
exposes a CLI with JSON and human-readable output and meaningful exit codes;
the two workflows are thin CLIs over those libraries.

- [`library-cli-convention.md`](./library-cli-convention.md) — the common
  contract every role/capability library CLI follows (I/O formats, exit
  codes, telemetry emission, secret redaction).
- [`spec-run-cli.md`](./spec-run-cli.md) — the Specification Workflow CLI
  (`spec-run`): text-in → approved `spec_version_id` out.
- [`dev-run-cli.md`](./dev-run-cli.md) — the Development Workflow CLI
  (`dev-run`): `spec_version_id`-in → opened PR out.