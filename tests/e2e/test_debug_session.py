"""End-to-end tests for complete debug sessions."""

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from python_debugger_mcp.core.session import SessionManager
from python_debugger_mcp.main import create_app
from python_debugger_mcp.persistence.breakpoints import BreakpointStore


async def wait_for_event(
    client: AsyncClient,
    session_id: str,
    event_type: str,
    timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> dict | None:
    """Poll for a specific event type until it arrives or timeout.

    Args:
        client: HTTP client
        session_id: Debug session ID
        event_type: Event type to wait for (e.g., "stopped", "terminated")
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds

    Returns:
        The event data if found, None otherwise
    """
    elapsed = 0.0
    all_events = []

    while elapsed < timeout:
        response = await client.get(
            f"/api/v1/sessions/{session_id}/events",
            params={"timeout": min(1.0, timeout - elapsed)},
        )
        if response.status_code == 200:
            events = response.json()["events"]
            all_events.extend(events)
            for event in events:
                if event["type"] == event_type:
                    return event

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval + 1.0  # Account for the long-poll timeout

    return None


async def wait_for_state(
    client: AsyncClient,
    session_id: str,
    target_state: str,
    timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> bool:
    """Poll until session reaches target state.

    Args:
        client: HTTP client
        session_id: Debug session ID
        target_state: State to wait for (e.g., "paused", "terminated")
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds

    Returns:
        True if state reached, False on timeout
    """
    elapsed = 0.0

    while elapsed < timeout:
        response = await client.get(f"/api/v1/sessions/{session_id}")
        if response.status_code == 200:
            state = response.json()["state"]
            if state == target_state:
                return True
            if state == "terminated" and target_state != "terminated":
                return False  # Session died

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    return False


@pytest_asyncio.fixture
async def debug_client(tmp_path):
    """Create test client with properly initialized app."""
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


@pytest.fixture
def simple_script(tmp_path) -> Path:
    """Create a simple Python script for debugging."""
    script = tmp_path / "simple.py"
    script.write_text("""
def greet(name):
    message = f"Hello, {name}!"
    print(message)
    return message

def main():
    result = greet("World")
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    main()
""")
    return script


@pytest.fixture
def loop_script(tmp_path) -> Path:
    """Create a script with a loop."""
    script = tmp_path / "loop.py"
    script.write_text("""
def process():
    total = 0
    for i in range(10):
        total += i
        print(f"i={i}, total={total}")
    return total

if __name__ == "__main__":
    result = process()
    print(f"Final: {result}")
""")
    return script


class TestBasicDebugSession:
    """Test basic debug session workflow."""

    @pytest.mark.asyncio
    async def test_create_launch_and_run(
        self, debug_client: AsyncClient, simple_script: Path, tmp_path: Path
    ) -> None:
        """Test creating a session, launching, and running to completion."""
        # 1. Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        assert response.status_code == 201
        session_id = response.json()["id"]

        # 2. Launch without breakpoints (should run to completion)
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(simple_script)},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

        # 3. Wait for terminated state
        terminated = await wait_for_state(debug_client, session_id, "terminated", timeout=10.0)
        assert terminated, "Session did not terminate"

        # 4. Check output was captured
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/output")
        assert response.status_code == 200
        output = response.json()

        # Should have captured print output
        content = "".join(line["content"] for line in output["lines"])
        assert "Hello, World!" in content

    @pytest.mark.asyncio
    async def test_breakpoint_and_inspect(
        self, debug_client: AsyncClient, simple_script: Path, tmp_path: Path
    ) -> None:
        """Test setting breakpoint, hitting it, and inspecting state."""
        # 1. Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = response.json()["id"]

        # 2. Set breakpoint on line 4 (message = f"Hello, {name}!")
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(simple_script),
                "breakpoints": [{"line": 4}],
            },
        )
        assert response.status_code == 200

        # 3. Launch (will hit breakpoint on line 4)
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(simple_script)},
        )
        assert response.status_code == 200

        # 4. Wait for session to pause at breakpoint
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=10.0)
        assert paused, "Session did not reach paused state"

        # 5. Verify session state
        response = await debug_client.get(f"/api/v1/sessions/{session_id}")
        assert response.json()["state"] == "paused"

        # 6. Get threads
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/threads")
        assert response.status_code == 200
        threads = response.json()["threads"]
        assert len(threads) > 0

        # 7. Get stack trace
        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/stacktrace",
            params={"thread_id": threads[0]["id"]},
        )
        assert response.status_code == 200
        frames = response.json()["frames"]
        assert len(frames) > 0

        # Top frame should be in greet function
        assert "greet" in frames[0]["name"]

        # 8. Get scopes for top frame
        frame_id = frames[0]["id"]
        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/scopes",
            params={"frame_id": frame_id},
        )
        assert response.status_code == 200
        scopes = response.json()["scopes"]
        assert len(scopes) > 0

        # 9. Get local variables
        locals_scope = next((s for s in scopes if s["name"] == "Locals"), scopes[0])
        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/variables",
            params={"ref": locals_scope["variables_reference"]},
        )
        assert response.status_code == 200
        variables = response.json()["variables"]

        # Should see 'name' parameter
        var_names = [v["name"] for v in variables]
        assert "name" in var_names

        # 10. Evaluate expression
        response = await debug_client.post(
            f"/api/v1/sessions/{session_id}/evaluate",
            json={"expression": "name.upper()", "frame_id": frame_id},
        )
        assert response.status_code == 200
        result = response.json()
        assert "WORLD" in result["result"]

        # 11. Continue to completion
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_step_operations(
        self, debug_client: AsyncClient, simple_script: Path, tmp_path: Path
    ) -> None:
        """Test step over, step into, step out."""
        # Create session and set breakpoint
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = response.json()["id"]

        # Set breakpoint at result = greet("World") - line 8
        await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(simple_script),
                "breakpoints": [{"line": 8}],  # result = greet("World")
            },
        )

        # Launch and wait for paused state (hit breakpoint)
        await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(simple_script)},
        )

        # Wait for paused state
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=10.0)
        assert paused, "Session did not pause at breakpoint"

        # Step into greet function
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/step-into")
        assert response.status_code == 200

        # Wait for paused state again after step
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=5.0)
        assert paused, "Session did not pause after step-into"

        # Verify we're in greet function
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/stacktrace")
        frames = response.json()["frames"]
        assert "greet" in frames[0]["name"]

        # Step out back to main
        response = await debug_client.post(f"/api/v1/sessions/{session_id}/step-out")
        assert response.status_code == 200


class TestConditionalBreakpoints:
    """Test conditional breakpoint functionality."""

    @pytest.mark.asyncio
    async def test_conditional_breakpoint(
        self, debug_client: AsyncClient, loop_script: Path, tmp_path: Path
    ) -> None:
        """Test that conditional breakpoint only hits when condition is true."""
        # Create session
        response = await debug_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = response.json()["id"]

        # Set conditional breakpoint - only break when i == 5
        await debug_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": str(loop_script),
                "breakpoints": [{"line": 5, "condition": "i == 5"}],  # total += i
            },
        )

        # Launch
        await debug_client.post(
            f"/api/v1/sessions/{session_id}/launch",
            json={"program": str(loop_script)},
        )

        # Wait for paused state (conditional breakpoint hit)
        paused = await wait_for_state(debug_client, session_id, "paused", timeout=10.0)
        assert paused, "Session did not pause at conditional breakpoint"

        # Get local variables - i should be 5
        response = await debug_client.get(f"/api/v1/sessions/{session_id}/stacktrace")
        assert response.status_code == 200
        frame_id = response.json()["frames"][0]["id"]

        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/scopes",
            params={"frame_id": frame_id},
        )
        locals_ref = response.json()["scopes"][0]["variables_reference"]

        response = await debug_client.get(
            f"/api/v1/sessions/{session_id}/variables",
            params={"ref": locals_ref},
        )
        variables = {v["name"]: v["value"] for v in response.json()["variables"]}

        # i should be 5 (when condition was true)
        assert "i" in variables
        assert variables["i"] == "5"
