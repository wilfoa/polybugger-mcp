"""Python (debugpy) adapter integration tests.

These tests verify the debugpy adapter works correctly for Python debugging.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from polybugger_mcp.adapters.debugpy_adapter import DebugpyAdapter
from polybugger_mcp.models.dap import LaunchConfig, SourceBreakpoint
from polybugger_mcp.models.events import EventType

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "python"


class TestDebugpyAdapter:
    """Test suite for Python debugpy adapter."""

    @pytest_asyncio.fixture
    async def adapter(self):  # type: ignore[misc]
        """Create debugpy adapter instance with cleanup."""
        _adapter = DebugpyAdapter(
            session_id="test-python-session",
            output_callback=None,
            event_callback=None,
        )
        yield _adapter
        # Cleanup
        try:
            await _adapter.disconnect()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_initialize(self, adapter: DebugpyAdapter) -> None:
        """Test adapter initialization."""
        capabilities = await adapter.initialize()

        assert adapter.is_initialized
        assert capabilities is not None
        assert isinstance(capabilities, dict)
        assert "supportsConfigurationDoneRequest" in capabilities

    @pytest.mark.asyncio
    async def test_launch_simple_script(self, adapter: DebugpyAdapter) -> None:
        """Test launching a simple Python script."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.py"

        # Track termination
        terminated = asyncio.Event()

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            if event_type == EventType.TERMINATED:
                terminated.set()

        adapter._event_callback = event_handler

        # Launch without breakpoints - should run to completion
        config = LaunchConfig(program=str(fixture), stop_on_entry=False)
        await adapter.launch(config)

        assert adapter.is_launched

        # Wait for termination
        await asyncio.wait_for(terminated.wait(), timeout=10.0)

    @pytest.mark.asyncio
    async def test_breakpoint_and_continue(self, adapter: DebugpyAdapter) -> None:
        """Test setting breakpoint, hitting it, and continuing."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.py"

        # Set up event tracking
        stopped = asyncio.Event()
        terminated = asyncio.Event()
        stopped_data: dict[str, Any] = {}

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            if event_type == EventType.STOPPED:
                stopped_data.update(data)
                stopped.set()
            elif event_type == EventType.TERMINATED:
                terminated.set()

        adapter._event_callback = event_handler

        # Configure callback to set breakpoints during launch sequence
        async def configure() -> None:
            await adapter.set_breakpoints(
                source_path=str(fixture),
                breakpoints=[SourceBreakpoint(line=6)],  # result = a + b
            )

        # Launch with configure callback
        config = LaunchConfig(program=str(fixture), stop_on_entry=False)
        await adapter.launch(config, configure_callback=configure)

        # Wait for breakpoint hit
        await asyncio.wait_for(stopped.wait(), timeout=10.0)
        assert stopped_data.get("reason") == "breakpoint"

        # Get thread id for continue (DAP uses camelCase)
        thread_id = stopped_data.get("threadId")
        assert thread_id is not None

        # Continue execution
        await adapter.continue_(thread_id)

        # Wait for termination
        await asyncio.wait_for(terminated.wait(), timeout=10.0)

    @pytest.mark.asyncio
    async def test_inspect_variables_at_breakpoint(self, adapter: DebugpyAdapter) -> None:
        """Test inspecting variables when stopped at breakpoint."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.py"

        stopped = asyncio.Event()
        stopped_thread_id: int | None = None

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_thread_id
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("threadId")  # DAP uses camelCase
                stopped.set()

        adapter._event_callback = event_handler

        # Configure callback to set breakpoints
        async def configure() -> None:
            await adapter.set_breakpoints(
                source_path=str(fixture),
                breakpoints=[SourceBreakpoint(line=6)],
            )

        # Launch with configure callback
        config = LaunchConfig(program=str(fixture))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=10.0)

        assert stopped_thread_id is not None

        # Get stack trace
        frames = await adapter.stack_trace(stopped_thread_id)
        assert len(frames) > 0
        assert frames[0].line == 6

        # Get scopes
        scopes = await adapter.scopes(frames[0].id)
        assert len(scopes) > 0

        # Find locals
        locals_scope = next((s for s in scopes if "local" in s.name.lower()), scopes[0])

        # Get variables
        variables = await adapter.variables(locals_scope.variables_reference)

        # Check 'a' and 'b' parameters
        var_names = [v.name for v in variables]
        assert "a" in var_names
        assert "b" in var_names

        var_a = next(v for v in variables if v.name == "a")
        assert "10" in var_a.value

    @pytest.mark.asyncio
    async def test_step_over(self, adapter: DebugpyAdapter) -> None:
        """Test stepping over a line."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.py"

        stopped = asyncio.Event()
        stopped_thread_id: int | None = None
        stop_count = 0

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_thread_id, stop_count
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("threadId")  # DAP uses camelCase
                stop_count += 1
                stopped.set()

        adapter._event_callback = event_handler

        async def configure() -> None:
            await adapter.set_breakpoints(
                source_path=str(fixture),
                breakpoints=[SourceBreakpoint(line=6)],
            )

        config = LaunchConfig(program=str(fixture))
        await adapter.launch(config, configure_callback=configure)

        # Wait for breakpoint
        await asyncio.wait_for(stopped.wait(), timeout=10.0)
        stopped.clear()

        assert stopped_thread_id is not None

        # Get initial position
        frames = await adapter.stack_trace(stopped_thread_id)
        initial_line = frames[0].line
        assert initial_line == 6

        # Step over
        await adapter.step_over(stopped_thread_id)

        # Wait for step completion
        await asyncio.wait_for(stopped.wait(), timeout=10.0)

        # Verify we moved
        frames = await adapter.stack_trace(stopped_thread_id)
        assert frames[0].line == 7  # return result

    @pytest.mark.asyncio
    async def test_evaluate_expression(self, adapter: DebugpyAdapter) -> None:
        """Test evaluating expressions at breakpoint."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.py"

        stopped = asyncio.Event()
        stopped_thread_id: int | None = None

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_thread_id
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("threadId")  # DAP uses camelCase
                stopped.set()

        adapter._event_callback = event_handler

        async def configure() -> None:
            await adapter.set_breakpoints(
                source_path=str(fixture),
                breakpoints=[SourceBreakpoint(line=6)],
            )

        config = LaunchConfig(program=str(fixture))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=10.0)

        assert stopped_thread_id is not None

        frames = await adapter.stack_trace(stopped_thread_id)
        frame_id = frames[0].id

        # Evaluate expression
        result = await adapter.evaluate("a + b", frame_id=frame_id)

        assert "result" in result
        assert result["result"] == "30"  # 10 + 20

    @pytest.mark.asyncio
    async def test_conditional_breakpoint(self, adapter: DebugpyAdapter) -> None:
        """Test conditional breakpoint only triggers when condition is true."""
        await adapter.initialize()

        # Create a script that calls function multiple times
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def check(x):
    result = x * 2  # Line 3
    return result

for i in range(5):
    check(i)
""")
            script_path = f.name

        stopped = asyncio.Event()
        stopped_data: dict[str, Any] = {}

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            if event_type == EventType.STOPPED:
                stopped_data.update(data)
                stopped.set()

        adapter._event_callback = event_handler

        # Configure callback with conditional breakpoint
        async def configure() -> None:
            await adapter.set_breakpoints(
                source_path=script_path,
                breakpoints=[SourceBreakpoint(line=3, condition="x == 3")],
            )

        config = LaunchConfig(program=script_path)
        await adapter.launch(config, configure_callback=configure)

        # Should stop when x == 3
        await asyncio.wait_for(stopped.wait(), timeout=10.0)

        # Verify we stopped at the right condition (DAP uses camelCase)
        thread_id = stopped_data.get("threadId")
        assert thread_id is not None
        frames = await adapter.stack_trace(thread_id)
        scopes = await adapter.scopes(frames[0].id)
        locals_scope = next((s for s in scopes if "local" in s.name.lower()), scopes[0])
        variables = await adapter.variables(locals_scope.variables_reference)

        var_x = next((v for v in variables if v.name == "x"), None)
        assert var_x is not None
        assert var_x.value == "3"

        # Cleanup temp file
        import os

        os.unlink(script_path)
