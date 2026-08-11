# User Session Timeout — Tasks

## Phase 1: Setup

1. [ ] T001 Create the session table migration.
   - File: `src/ai_factory/sessions/migrations/1_session_table.py`

2. [ ] T002 Add the session model.
   - File: `src/ai_factory/sessions/models.py`

## Phase 2: Core

3. [ ] T003 Implement the expiry reaper job.
   - File: `src/ai_factory/sessions/reaper.py`

4. [ ] T004 Add the session refresh middleware. [P]
   - File: `src/ai_factory/web/session_middleware.py`

5. [ ] T005 Add the admin active-sessions view. [P]
   - File: `src/ai_factory/admin/sessions_view.py`

## Phase 3: Tests

6. [ ] T006 Unit tests for the reaper.
   - File: `tests/unit/sessions/test_reaper.py`

7. [ ] T007 Integration tests for the middleware. [P]
   - File: `tests/integration/web/test_session_middleware.py`
