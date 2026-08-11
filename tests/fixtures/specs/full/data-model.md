# User Session Timeout — Data Model

Optional supporting artifact for the full fixture.

## Entities

- `Session`: id, user_id, token_hash, last_activity_at, created_at.
- `UserSessionView`: read-only projection for admin listing.
