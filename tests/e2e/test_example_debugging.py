"""End-to-end tests for debugging example scripts.

These tests verify the debug relay server works correctly by debugging
standalone example scripts that don't use debugpy themselves.
"""

import asyncio
from pathlib import Path
from typing import Optional

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from opencode_debugger.core.session import SessionManager
from opencode_debugger.main import create_app
from opencode_debugger.persistence.breakpoints import BreakpointStore


# Path to examples directory
EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"


async def wait_for_state(
    client: AsyncClient,
    session_id: str,
    target_state: str,
    timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> bool:
    """Poll until session reaches target state."""
    elapsed = 0.0
    while elapsed < timeout:
        response = await client.get(f"/api/v1/sessions/{session_id}")
        if response.status_code == 200:
            state = response.json()["state"]
            if state == target_state:
                return True
            if state == "terminated" and target_state != "terminated":
                return False
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    return False


@pytest_asyncio.fixture
async def debug_client(tmp_path: Path):
    """Create test client with debug server."""
    app = create_app()
    breakpoint_store = BreakpointStore(base_dir=tmp_path / "breakpoints")
    session_manager = SessionManager(breakpoint_store=breakpoint_store)
    await session_manager.start()
    app.state.session_manager = session_manager

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session_manager.stop()


class TestFibonacciDebugging:
    """Test debugging the Fibonacci example script."""

    @pytest.mark.asyncio
    async def test_debug_fibonacci_with_breakpoint(
        self, debug_client: AsyncClient, tmp_path: Path
    ) -> None:
        """Test setting a breakpoint in fibonacci and inspecting variables."""
        fibonacci_script = EXAMPLES_DIR / "fibonacci.py"
        assert fibonacci_script.exists(), f"Example script not found: {fibonacci_script}"

        # Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(EXAMPLES_DIR)},
        )
        assert response.status_code == 201
        session_id = response.json()["id"]

        # Set breakpoint on line 23 (return b - only hit once per call)
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(fibonacci_script),
                "breakpoints": [{"line": 23}],  # return b
            },
        )
        assert response.status_code == 200

        # Launch
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(fibonacci_script)},
        )
        assert response.status_code == 200

        # Wait for paused state
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=10.0)
        assert paused, "Session did not pause at breakpoint"

        # Get stack trace
        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/stacktrace",
            params={"thread_id": 1},
        )
        assert response.status_code == 200
        frames = response.json()["frames"]
        assert len(frames) > 0
        assert "fibonacci_iterative" in frames[0]["name"]

        # Get scopes
        frame_id = frames[0]["id"]
        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/scopes",
            params={"frame_id": frame_id},
        )
        assert response.status_code == 200
        scopes = response.json()["scopes"]
        assert len(scopes) > 0

        # Get local variables
        locals_scope = next((s for s in scopes if s["name"] == "Locals"), scopes[0])
        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/variables",
            params={"ref": locals_scope["variables_reference"]},
        )
        assert response.status_code == 200
        variables = response.json()["variables"]
        var_names = [v["name"] for v in variables]
        
        # Should have 'n', 'a', 'b' in scope
        assert "n" in var_names
        assert "a" in var_names
        assert "b" in var_names

        # Clear breakpoints so continue doesn't hit them again
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(fibonacci_script),
                "breakpoints": [],  # Clear all breakpoints
            },
        )
        assert response.status_code == 200

        # Continue to completion
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code == 200

        # Wait for termination
        terminated = await wait_for_state(debug_client, session_id, "terminated", timeout=15.0)
        assert terminated

    @pytest.mark.asyncio
    async def test_step_through_fibonacci(
        self, debug_client: AsyncClient, tmp_path: Path
    ) -> None:
        """Test stepping through the fibonacci function."""
        fibonacci_script = EXAMPLES_DIR / "fibonacci.py"

        # Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(EXAMPLES_DIR)},
        )
        session_id = response.json()["id"]

        # Set breakpoint at start of fibonacci function (line 5)
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(fibonacci_script),
                "breakpoints": [{"line": 6}],  # if n <= 0:
            },
        )
        assert response.status_code == 200

        # Launch
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(fibonacci_script)},
        )
        assert response.status_code == 200

        # Wait for breakpoint
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=10.0)
        assert paused

        # Verify we're in fibonacci
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/stacktrace")
        frames = response.json()["frames"]
        assert "fibonacci" in frames[0]["name"]

        # Step over
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/step-over")
        assert response.status_code == 200

        # Wait for pause after step
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=5.0)
        assert paused

        # Continue to end
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code == 200


class TestDataProcessorDebugging:
    """Test debugging the data processor example script."""

    @pytest.mark.asyncio
    async def test_debug_filter_records(
        self, debug_client: AsyncClient, tmp_path: Path
    ) -> None:
        """Test debugging the filter_records function."""
        processor_script = EXAMPLES_DIR / "data_processor.py"
        assert processor_script.exists(), f"Example script not found: {processor_script}"

        # Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(EXAMPLES_DIR)},
        )
        session_id = response.json()["id"]

        # Set breakpoint inside filter_records (line 39 - if predicate(record):)
        # Line 38 is the for loop header, line 39 is inside the loop where record exists
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(processor_script),
                "breakpoints": [{"line": 39}],  # if predicate(record):
            },
        )
        assert response.status_code == 200

        # Launch
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(processor_script)},
        )
        assert response.status_code == 200

        # Wait for breakpoint
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=10.0)
        assert paused

        # Check we're in filter_records
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/stacktrace")
        frames = response.json()["frames"]
        assert "filter_records" in frames[0]["name"]

        # Evaluate an expression - check the current record
        frame_id = frames[0]["id"]
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/evaluate",
            json={"expression": "record.name", "frame_id": frame_id},
        )
        assert response.status_code == 200
        result = response.json()
        # First record name should be present (depends on which record is first being filtered)
        assert "result" in result

        # Continue
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_conditional_breakpoint_in_transform(
        self, debug_client: AsyncClient, tmp_path: Path
    ) -> None:
        """Test conditional breakpoint that only triggers for specific records."""
        processor_script = EXAMPLES_DIR / "data_processor.py"

        # Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(EXAMPLES_DIR)},
        )
        session_id = response.json()["id"]

        # Set conditional breakpoint - only break when old_value > 25
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(processor_script),
                "breakpoints": [{"line": 55, "condition": "old_value > 25"}],  # new_value = transformer(old_value)
            },
        )
        assert response.status_code == 200

        # Launch
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(processor_script)},
        )
        assert response.status_code == 200

        # Wait for breakpoint
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=10.0)
        assert paused

        # Evaluate old_value - should be > 25
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/stacktrace")
        frame_id = response.json()["frames"][0]["id"]

        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/evaluate",
            json={"expression": "old_value", "frame_id": frame_id},
        )
        assert response.status_code == 200
        result = response.json()
        # Extract numeric value and verify > 25
        value_str = result["result"]
        # Value should be a float > 25
        assert float(value_str) > 25

        # Continue to completion
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code == 200


class TestOutputCapture:
    """Test that program output is captured correctly."""

    @pytest.mark.asyncio
    async def test_capture_fibonacci_output(
        self, debug_client: AsyncClient, tmp_path: Path
    ) -> None:
        """Test that output from fibonacci script is captured."""
        fibonacci_script = EXAMPLES_DIR / "fibonacci.py"

        # Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(EXAMPLES_DIR)},
        )
        session_id = response.json()["id"]

        # Launch without breakpoints - run to completion
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(fibonacci_script)},
        )
        assert response.status_code == 200

        # Wait for completion
        terminated = await wait_for_state(debug_client, session_id, "terminated", timeout=15.0)
        assert terminated

        # Get output
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/output")
        assert response.status_code == 200
        output = response.json()

        # Combine all output lines
        content = "".join(line["content"] for line in output["lines"])

        # Should contain expected output
        assert "Fibonacci Calculator" in content
        assert "fib(0) = 0" in content
        assert "fib(1) = 1" in content
        assert "Done!" in content
