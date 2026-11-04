# Development guide

## Structure and dependency direction

```text
backend/
  app/
    main.py                 FastAPI composition root and app factory
    lifecycle.py            Startup recovery and shutdown
    api/                    HTTP/WebSocket routes, schemas, authentication middleware
      catalog.py            Exercises and criteria
      cameras.py            Preview, readiness and calibration
      training.py           Session and attempt lifecycle
      reports.py            History, exports, progress and deletion
      system.py             Health, status, clock and WebSocket
      schemas.py            Pydantic request validation
      dependencies.py       Ownership checks and single-device operation lock
    services/reporting.py   Assemble full session reports
    repositories/
      report_queries.py     Efficient catalog, history-list and progress queries
    database.py             SQLAlchemy models, connection and initialization
    calibration.py          Pure homography calculation used by API and CLI
    paths.py                Stable project/backend filesystem roots
    m1_assessment.py        M1 posture assessment
    m2_follow_through.py     M2 red-gate and estimated cue-tip assessment
    contact.py              M3 contact geometry
    runtime.py              Camera worker and recording coordination
  tests/                    Offline automated tests, named test_*.py
  tools/                    CLI checks, calibration, exports and evaluation
  pyproject.toml            Ruff lint and formatting configuration
  requirements*.txt         Runtime, camera and development dependencies
frontend/ai-snooker/
  src/pages/                Screens for the user
  src/components/           Reusable UI and WorkspacePages screen selection
  src/hooks/                Connection, data loading and display timing
  src/lib/                  API client and testable UI logic
  src/Workspace.jsx         Training orchestration and shared workspace state
  tools/                    Offline frontend checks
```

Routes may call services and repositories. Repositories do not import API routes.
Camera processing and assessment modules do not import the FastAPI entry point.
Command-line tools call application functions; application code does not import tools.
Request validation belongs in `api/schemas.py`; database queries should not be placed in UI code.
Runtime PostgreSQL remains configured by `DATABASE_URL`. The in-memory SQLite fixture in
`tests/test_report_loading.py` is only an isolated query test and never stores training records.

## Local tools

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check backend/app backend/tools backend/tests
.\.venv\Scripts\python.exe -m ruff format --check backend/app backend/tools backend/tests scripts
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p "test_*.py"
```

Run frontend commands from `frontend/ai-snooker`:

```powershell
npm ci
npm run lint
npm run format:check
npm run test
npm run build
```

To format edited code, use `python -m ruff format` for Python and `npm run format`
for the frontend. `.editorconfig` specifies UTF-8, LF endings and indentation.
`ruff`, `prettier` and the test runner are development tools, not production features.

## Change and verification rules

- Keep public API URLs and payloads compatible unless both client and API are updated.
- Keep assessment criteria changes separate from structural refactoring.
- Scope history queries, media access and deletion to the authenticated profile.
- Keep timestamps, raw observations, missing-data status and criteria versions auditable.
- Tests use generated records, mocked connections or isolated in-memory databases.
  Never point automated tests at a database containing real training records.
- Offline checks do not certify real-camera accuracy. Validate M1–M3 on the actual setup.
- M4 remains a preview screen; do not represent it as an operational assessment.

The start scripts and `uvicorn app.main:app` entry point remain unchanged.
