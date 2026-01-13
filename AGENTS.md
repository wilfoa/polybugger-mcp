# OpenCode Debug Relay Server

## Project Overview

This is a Python HTTP server that enables AI agents to debug Python code interactively. It translates REST API calls to DAP (Debug Adapter Protocol) messages for debugpy.

## Tech Stack

- **Language:** Python 3.13+
- **Framework:** FastAPI with uvicorn
- **Debugger:** debugpy (Python debugger)
- **Testing:** pytest with pytest-asyncio
- **Package Manager:** pip with pyproject.toml

## Project Structure

```
src/opencode_debugger/
  api/           # FastAPI routers (sessions, breakpoints, execution, inspection, output)
  adapters/      # DAP client and debugpy adapter
  core/          # Session management, events, exceptions
  models/        # Pydantic models (DAP, requests, responses)
  persistence/   # Breakpoint storage
  utils/         # Output buffer
  config.py      # Pydantic Settings configuration
  main.py        # FastAPI app entry point

tests/
  unit/          # Unit tests for buffer and persistence
  integration/   # API integration tests
  e2e/           # End-to-end debug session tests
```

## Running the Project

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the server
python -m opencode_debugger.main

# Run tests
pytest tests/ -v
```

## Debugging This Project

This project includes its own debugging tools as an OpenCode skill and plugin.

### Using the Debug Tools

1. **Start the debug server** (in a separate terminal):
   ```bash
   source .venv/bin/activate
   python -m opencode_debugger.main
   ```

2. **Use the debug-* tools** to debug Python code in this project:
   - `debug-session-create` - Create a session with project_root="/Users/amir/Development/opencode_debugger"
   - `debug-breakpoints` - Set breakpoints in source files
   - `debug-launch` - Launch test scripts or the server itself
   - `debug-stacktrace`, `debug-variables`, `debug-evaluate` - Inspect state

### Debugging Tests

To debug a failing test:
1. Create a debug session for this project
2. Set breakpoints in the test file or source code
3. Launch with: `program="path/to/test.py"` or `module="pytest"` with `args=["-xvs", "tests/path/to/test.py::test_name"]`

## Code Patterns

- **Async/await:** All I/O operations are async
- **Pydantic models:** Used for all API request/response validation
- **DAP protocol:** Communication with debugpy follows DAP specification
- **State machine:** Sessions have defined state transitions (created -> launching -> running/paused -> terminated)

## Key Files

- `src/opencode_debugger/adapters/debugpy_adapter.py` - Core debugpy communication
- `src/opencode_debugger/core/session.py` - Session management and state machine
- `src/opencode_debugger/api/sessions.py` - Session API endpoints
- `tests/e2e/test_debug_session.py` - End-to-end debugging tests
