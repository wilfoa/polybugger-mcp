"""Go (delve) adapter integration tests.

These tests verify the delve adapter works correctly for Go debugging.
Tests are skipped if dlv is not available.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from pybugger_mcp.adapters.delve_adapter import DelveAdapter, GoLaunchConfig
from pybugger_mcp.models.dap import SourceBreakpoint
from pybugger_mcp.models.events import EventType

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "go"

# Skip all tests if dlv is not installed
pytestmark = pytest.mark.skipif(
    shutil.which("dlv") is None,
    reason="dlv not installed (go install github.com/go-delve/delve/cmd/dlv@latest)",
)


class TestDelveAdapter:
    """Test suite for Go delve adapter."""

    @pytest_asyncio.fixture
    async def adapter(self):  # type: ignore[misc]
        """Create delve adapter instance with cleanup."""
        _adapter = DelveAdapter(
            session_id="test-go-session",
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
    async def test_initialize(self, adapter: DelveAdapter) -> None:
        """Test adapter initialization."""
        capabilities = await adapter.initialize()

        assert adapter.is_connected
        assert capabilities is not None
        assert isinstance(capabilities, dict)

    @pytest.mark.asyncio
    async def test_launch_simple_program(self, adapter: DelveAdapter) -> None:
        """Test launching a simple Go program."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.go"

        # Track termination
        terminated = asyncio.Event()

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            if event_type == EventType.TERMINATED:
                terminated.set()

        adapter._event_callback = event_handler

        # Launch without breakpoints - should run to completion
        config = GoLaunchConfig(program=str(fixture), stop_on_entry=False)
        await adapter.launch(config)

        assert adapter.is_launched

        # Wait for termination
        await asyncio.wait_for(terminated.wait(), timeout=30.0)

    @pytest.mark.asyncio
    async def test_breakpoint_and_continue(self, adapter: DelveAdapter) -> None:
        """Test setting breakpoint, hitting it, and continuing."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.go"

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
                breakpoints=[SourceBreakpoint(line=7)],  # result := a + b (inside calculate)
            )

        # Launch with configure callback
        config = GoLaunchConfig(program=str(fixture), stop_on_entry=False)
        await adapter.launch(config, configure_callback=configure)

        # Wait for breakpoint hit
        await asyncio.wait_for(stopped.wait(), timeout=30.0)
        assert stopped_data.get("reason") == "breakpoint"

        # Get thread id for continue (DAP uses camelCase)
        thread_id = stopped_data.get("threadId")
        assert thread_id is not None

        # Continue execution
        await adapter.continue_execution(thread_id)

        # Wait for termination
        await asyncio.wait_for(terminated.wait(), timeout=30.0)

    @pytest.mark.asyncio
    async def test_inspect_variables_at_breakpoint(self, adapter: DelveAdapter) -> None:
        """Test inspecting variables when stopped at breakpoint."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.go"

        stopped = asyncio.Event()
        stopped_thread_id: int | None = None

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_thread_id
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("threadId")
                stopped.set()

        adapter._event_callback = event_handler

        # Configure callback to set breakpoints
        async def configure() -> None:
            await adapter.set_breakpoints(
                source_path=str(fixture),
                breakpoints=[SourceBreakpoint(line=7)],  # result := a + b (inside calculate)
            )

        # Launch with configure callback
        config = GoLaunchConfig(program=str(fixture))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=30.0)

        assert stopped_thread_id is not None

        # Get stack trace
        frames = await adapter.get_stack_trace(stopped_thread_id)
        assert len(frames) > 0

        # Get scopes
        scopes = await adapter.get_scopes(frames[0].id)
        assert len(scopes) > 0

        # Find locals scope - delve may name it differently
        locals_scope = next(
            (s for s in scopes if "local" in s.name.lower() or s.name == "Locals"),
            scopes[0],
        )

        # Get variables
        variables = await adapter.get_variables(locals_scope.variables_reference)

        # Check 'a' and 'b' parameters exist (may be in arguments scope for Go)
        var_names = [v.name for v in variables]
        # In Go, function parameters may be in a separate "Arguments" scope
        if "a" not in var_names and "b" not in var_names:
            # Try to find arguments scope
            args_scope = next(
                (s for s in scopes if "arg" in s.name.lower() or s.name == "Arguments"),
                None,
            )
            if args_scope:
                arg_vars = await adapter.get_variables(args_scope.variables_reference)
                var_names.extend([v.name for v in arg_vars])

        assert "a" in var_names, f"Expected 'a' in {var_names}"
        assert "b" in var_names, f"Expected 'b' in {var_names}"

    @pytest.mark.asyncio
    async def test_evaluate_expression(self, adapter: DelveAdapter) -> None:
        """Test evaluating expressions at breakpoint."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.go"

        stopped = asyncio.Event()
        stopped_thread_id: int | None = None

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_thread_id
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("threadId")
                stopped.set()

        adapter._event_callback = event_handler

        async def configure() -> None:
            await adapter.set_breakpoints(
                source_path=str(fixture),
                breakpoints=[SourceBreakpoint(line=7)],  # result := a + b (inside calculate)
            )

        config = GoLaunchConfig(program=str(fixture))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=30.0)

        assert stopped_thread_id is not None

        frames = await adapter.get_stack_trace(stopped_thread_id)
        frame_id = frames[0].id

        # Evaluate expression
        result = await adapter.evaluate("a + b", frame_id=frame_id)

        assert "result" in result
        # Delve returns the result as a string, may include type info
        assert "30" in str(result["result"]), f"Expected '30' in {result}"
