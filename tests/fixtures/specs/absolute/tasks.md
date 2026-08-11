# Logging Library — Tasks

## Phase 1: Setup

1. [ ] T001 Create the logging package skeleton.
   - File: `src/ai_factory/logging/__init__.py`

## Phase 2: Core

2. [ ] T002 Implement the JSON formatter.
   - File: `src/ai_factory/logging/json_formatter.py`

3. [ ] T003 Wire the library into the app.
   - File: `/etc/app/logging_config.py` (absolute, outside repo)
   - File: `C:\\Users\\dev\\app\\logger.py` (absolute host path)

4. [ ] T004 Add the telemetry sink. [P]
   - File: `src/ai_factory/logging/telemetry_sink.py`
   - File: `src/ai_factory/shared/telemetry/store.py` (shares file with existing lib)
