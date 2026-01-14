"""Standalone script to debug the E2E test logic."""

import asyncio
import tempfile
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from python_debugger_mcp.core.session import SessionManager
from python_debugger_mcp.main import create_app
from python_debugger_mcp.persistence.breakpoints import BreakpointStore


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
            print(f"  Current state: {state}")
            if state == target_state:
                return True
            if state == "terminated" and target_state != "terminated":
                return False

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    return False


async def run_test():
    """Run the test_create_launch_and_run logic."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create simple script
        simple_script = tmp_path / "simple.py"
        simple_script.write_text("""
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

        # Create app with session manager
        app = create_app()
        breakpoint_store = BreakpointStore(base_dir=tmp_path / "breakpoints")
        session_manager = SessionManager(breakpoint_store=breakpoint_store)
        await session_manager.start()
        app.state.session_manager = session_manager

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                print("1. Creating session...")
                response = await client.post(
                    "/api/v1/sessions",
                    json={"project_root": str(tmp_path)},
                )
                assert (
                    response.status_code == 201
                ), f"Expected 201, got {response.status_code}: {response.text}"
                session_id = response.json()["id"]
                print(f"   Created session: {session_id}")

                print("2. Launching program...")
                response = await client.post(
                    f"/api/v1/sessions/{session_id}/launch",
                    json={"program": str(simple_script)},
                )
                assert (
                    response.status_code == 200
                ), f"Expected 200, got {response.status_code}: {response.text}"
                assert response.json()["status"] == "running"
                print("   Program launched successfully")

                print("3. Waiting for termination...")
                terminated = await wait_for_state(client, session_id, "terminated", timeout=10.0)
                assert terminated, "Session did not terminate"
                print("   Session terminated")

                print("4. Checking output...")
                response = await client.get(f"/api/v1/sessions/{session_id}/output")
                assert response.status_code == 200
                output = response.json()
                content = "".join(line["content"] for line in output["lines"])
                print(f"   Output: {content!r}")
                assert "Hello, World!" in content, "Expected 'Hello, World!' in output"

                print("\nTEST PASSED!")

        finally:
            await session_manager.stop()


if __name__ == "__main__":
    asyncio.run(run_test())
