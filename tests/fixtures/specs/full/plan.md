# User Session Timeout — Plan

Technical plan for the user session timeout feature.

## Tech Stack

- Python 3.14, src-layout package `ai_factory`.
- Persistence via Postgres with SQLAlchemy 2.0.
- New session expiry middleware in the web layer.

## Architecture Decisions

- AD-001: A background reaper job scans for idle sessions every 5 minutes.
- AD-002: Session metadata is stored in a dedicated `sessions` table indexed on
  `last_activity_at`.
- AD-003: Expiry policy is configurable via a `SESSION_IDLE` env var (default 30m).

## Security

- Session tokens are stored hashed (SHA-256), never in plaintext.
- The reaper logs contain no PII; session IDs are redacted.

## Risks

- Expiry race between reaper and request refresh is considered acceptable.

## Test Strategy

- Unit tests for the reaper, integration tests for the middleware.
