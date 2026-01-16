"""Node.js (js-debug) adapter integration tests.

These tests verify the Node.js adapter works correctly for JavaScript debugging.
Tests are skipped if js-debug CLI is not available.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from polybugger_mcp.adapters.node_adapter import NodeAdapter, NodeLaunchConfig
from polybugger_mcp.models.dap import SourceBreakpoint
from polybugger_mcp.models.events import EventType

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "javascript"

# Skip all tests if js-debug is not installed
pytestmark = pytest.mark.skipif(
    shutil.which("js-debug") is None,
    reason="js-debug CLI not installed (npm install -g @vscode/js-debug-cli)",
)


class TestNodeAdapter:
    """Test suite for Node.js js-debug adapter."""

    @pytest_asyncio.fixture
    async def adapter(self):  # type: ignore[misc]
        """Create Node.js adapter instance with cleanup."""
        _adapter = NodeAdapter(
            session_id="test-node-session",
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
    async def test_initialize(self, adapter: NodeAdapter) -> None:
        """Test adapter initialization."""
        capabilities = await adapter.initialize()

        assert adapter.is_connected
        assert capabilities is not None
        assert isinstance(capabilities, dict)

    @pytest.mark.asyncio
    async def test_launch_simple_script(self, adapter: NodeAdapter) -> None:
        """Test launching a simple JavaScript script."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.js"

        # Track termination
        terminated = asyncio.Event()

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            if event_type == EventType.TERMINATED:
                terminated.set()

        adapter._event_callback = event_handler

        # Launch without breakpoints - should run to completion
        config = NodeLaunchConfig(program=str(fixture), stop_on_entry=False)
        await adapter.launch(config)

        assert adapter.is_launched

        # Wait for termination
        await asyncio.wait_for(terminated.wait(), timeout=15.0)

    @pytest.mark.asyncio
    async def test_breakpoint_and_continue(self, adapter: NodeAdapter) -> None:
        """Test setting breakpoint, hitting it, and continuing."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.js"

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
                breakpoints=[SourceBreakpoint(line=7)],  # result = a + b
            )

        # Launch with configure callback
        config = NodeLaunchConfig(program=str(fixture), stop_on_entry=False)
        await adapter.launch(config, configure_callback=configure)

        # Wait for breakpoint hit
        await asyncio.wait_for(stopped.wait(), timeout=15.0)
        assert stopped_data.get("reason") == "breakpoint"

        # Get thread id for continue (DAP uses camelCase)
        thread_id = stopped_data.get("threadId")
        assert thread_id is not None

        # Continue execution
        await adapter.continue_execution(thread_id)

        # Wait for termination
        await asyncio.wait_for(terminated.wait(), timeout=15.0)

    @pytest.mark.asyncio
    async def test_inspect_variables_at_breakpoint(self, adapter: NodeAdapter) -> None:
        """Test inspecting variables when stopped at breakpoint."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.js"

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
                breakpoints=[SourceBreakpoint(line=7)],
            )

        # Launch with configure callback
        config = NodeLaunchConfig(program=str(fixture))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=15.0)

        assert stopped_thread_id is not None

        # Get stack trace
        frames = await adapter.get_stack_trace(stopped_thread_id)
        assert len(frames) > 0

        # Get scopes
        scopes = await adapter.get_scopes(frames[0].id)
        assert len(scopes) > 0

        # Find locals
        locals_scope = next((s for s in scopes if "local" in s.name.lower()), scopes[0])

        # Get variables
        variables = await adapter.get_variables(locals_scope.variables_reference)

        # Check 'a' and 'b' parameters exist
        var_names = [v.name for v in variables]
        assert "a" in var_names
        assert "b" in var_names

    @pytest.mark.asyncio
    async def test_evaluate_expression(self, adapter: NodeAdapter) -> None:
        """Test evaluating expressions at breakpoint."""
        await adapter.initialize()

        fixture = FIXTURES_DIR / "simple.js"

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
                breakpoints=[SourceBreakpoint(line=7)],
            )

        config = NodeLaunchConfig(program=str(fixture))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=15.0)

        assert stopped_thread_id is not None

        frames = await adapter.get_stack_trace(stopped_thread_id)
        frame_id = frames[0].id

        # Evaluate expression
        result = await adapter.evaluate("a + b", frame_id=frame_id)

        assert "result" in result
        assert result["result"] == "30"  # 10 + 20
