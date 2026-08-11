# Full Fixture — User Session Timeout

This is a complete, well-formed speckit folder used as the canonical fixture for
the folder-adapter tests. It contains a spec, a plan, and tasks, and exercises
every feature the adapter must handle deterministically.

## Functional Requirements

- FR-001: Idle sessions must expire after 30 minutes. (MUST, security relevant)
- FR-002: Expired sessions must force the user to re-authenticate. (SHOULD)
- FR-003: Active sessions must be refreshed on read/write.
- FR-004: Admin must be able to view all active sessions. (MUST)

## Non-Goals

- Multi-factor authentication is out of scope for this feature.

## Acceptance Criteria

- [ ] A-1: Constructing a folder with spec, plan, and tasks must succeed.
- [ ] A-2: A session does not exceed 30 minutes of idle time.
- [ ] A-3: The parser must preserve tasks.md ordering exactly.
