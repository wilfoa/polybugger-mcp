"""Base test class for debug adapter tests.

This module provides a base test class that defines common debug scenarios.
Each language adapter can inherit from this to run the same tests against
their specific adapter implementation.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pytest

from polybugger_mcp.adapters.base import DebugAdapter, LaunchConfig
from polybugger_mcp.models.events import EventType


class AdapterTestBase(ABC):
    """Base class for adapter integration tests.

    Subclasses must implement:
    - adapter_fixture: Return configured adapter instance
    - fixture_file: Return path to test fixture
    - breakpoint_line: Return line number for breakpoint test
    - expected_variable: Return (name, expected_value) for variable test

    These tests verify that an adapter correctly:
    1. Initializes and connects to the debug server
    2. Sets breakpoints
    3. Launches and stops at breakpoints
    4. Inspects variables
    5. Steps through code
    6. Continues and terminates
    """

    @pytest.fixture
    @abstractmethod
    def adapter(self) -> DebugAdapter:
        """Create and return adapter instance for testing."""
        ...

    @property
    @abstractmethod
    def fixture_file(self) -> Path:
        """Path to the test fixture source file."""
        ...

    @property
    @abstractmethod
    def breakpoint_line(self) -> int:
        """Line number to set breakpoint on."""
        ...

    @property
    @abstractmethod
    def expected_variable(self) -> tuple[str, Any]:
        """Variable name and expected value to check when stopped."""
        ...

    @property
    def call_line(self) -> int:
        """Line number where function is called (for step-into test)."""
        return self.breakpoint_line

    # =========================================================================
    # Common Test Methods
    # =========================================================================

    @pytest.mark.asyncio
    async def test_initialize(self, adapter: DebugAdapter) -> None:
        """Test adapter initialization."""
        capabilities = await adapter.initialize()

        assert adapter.is_connected
        assert capabilities is not None
        assert isinstance(capabilities, dict)

        # Most DAP adapters support these
        assert "supportsConfigurationDoneRequest" in capabilities

        await adapter.terminate()

    @pytest.mark.asyncio
    async def test_set_breakpoint(self, adapter: DebugAdapter) -> None:
        """Test setting a breakpoint."""
        await adapter.initialize()

        from polybugger_mcp.models.dap import SourceBreakpoint

        breakpoints = await adapter.set_breakpoints(
            source_path=str(self.fixture_file),
            breakpoints=[SourceBreakpoint(line=self.breakpoint_line)],
        )

        assert len(breakpoints) == 1
        assert breakpoints[0].verified is True
        assert breakpoints[0].line == self.breakpoint_line

        await adapter.terminate()

    @pytest.mark.asyncio
    async def test_launch_and_hit_breakpoint(self, adapter: DebugAdapter) -> None:
        """Test launching program and hitting breakpoint."""
        await adapter.initialize()

        from polybugger_mcp.models.dap import SourceBreakpoint

        # Set breakpoint
        await adapter.set_breakpoints(
            source_path=str(self.fixture_file),
            breakpoints=[SourceBreakpoint(line=self.breakpoint_line)],
        )

        # Track if we hit the breakpoint
        stopped_event = asyncio.Event()
        stopped_data: dict[str, Any] = {}

        original_callback = adapter._event_callback

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            if event_type == EventType.STOPPED:
                stopped_data.update(data)
                stopped_event.set()
            if original_callback:
                await original_callback(event_type, data)

        adapter._event_callback = event_handler

        # Launch
        config = LaunchConfig(
            program=str(self.fixture_file),
            stop_on_entry=False,
        )
        await adapter.launch(config)

        # Wait for breakpoint hit
        try:
            await asyncio.wait_for(stopped_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for breakpoint hit")

        assert stopped_data.get("reason") == "breakpoint"

        await adapter.terminate()

    @pytest.mark.asyncio
    async def test_inspect_variables(self, adapter: DebugAdapter) -> None:
        """Test inspecting variables when stopped."""
        await adapter.initialize()

        from polybugger_mcp.models.dap import SourceBreakpoint

        # Set breakpoint
        await adapter.set_breakpoints(
            source_path=str(self.fixture_file),
            breakpoints=[SourceBreakpoint(line=self.breakpoint_line)],
        )

        stopped_event = asyncio.Event()
        stopped_thread_id: int | None = None

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_thread_id
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("thread_id")
                stopped_event.set()

        adapter._event_callback = event_handler

        # Launch and wait for stop
        config = LaunchConfig(program=str(self.fixture_file))
        await adapter.launch(config)

        await asyncio.wait_for(stopped_event.wait(), timeout=10.0)
        assert stopped_thread_id is not None

        # Get stack trace
        frames = await adapter.get_stack_trace(stopped_thread_id)
        assert len(frames) > 0

        # Get scopes for top frame
        scopes = await adapter.get_scopes(frames[0].id)
        assert len(scopes) > 0

        # Find locals scope
        locals_scope = next((s for s in scopes if "local" in s.name.lower()), scopes[0])

        # Get variables
        variables = await adapter.get_variables(locals_scope.variables_reference)

        # Check expected variable
        var_name, expected_value = self.expected_variable
        var = next((v for v in variables if v.name == var_name), None)
        assert var is not None, f"Variable '{var_name}' not found"
        assert str(expected_value) in var.value

        await adapter.terminate()

    @pytest.mark.asyncio
    async def test_step_over(self, adapter: DebugAdapter) -> None:
        """Test stepping over a line."""
        await adapter.initialize()

        from polybugger_mcp.models.dap import SourceBreakpoint

        await adapter.set_breakpoints(
            source_path=str(self.fixture_file),
            breakpoints=[SourceBreakpoint(line=self.breakpoint_line)],
        )

        stopped_event = asyncio.Event()
        stopped_line: int | None = None
        stopped_thread_id: int | None = None

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_line, stopped_thread_id
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("thread_id")
                stopped_event.set()

        adapter._event_callback = event_handler

        config = LaunchConfig(program=str(self.fixture_file))
        await adapter.launch(config)

        # Wait for initial breakpoint
        await asyncio.wait_for(stopped_event.wait(), timeout=10.0)
        stopped_event.clear()

        assert stopped_thread_id is not None

        # Get initial line
        frames = await adapter.get_stack_trace(stopped_thread_id)
        initial_line = frames[0].line

        # Step over
        await adapter.step_over(stopped_thread_id)

        # Wait for step to complete
        await asyncio.wait_for(stopped_event.wait(), timeout=10.0)

        # Verify we moved to next line
        frames = await adapter.get_stack_trace(stopped_thread_id)
        assert frames[0].line != initial_line

        await adapter.terminate()

    @pytest.mark.asyncio
    async def test_continue_to_completion(self, adapter: DebugAdapter) -> None:
        """Test continuing execution to program completion."""
        await adapter.initialize()

        from polybugger_mcp.models.dap import SourceBreakpoint

        await adapter.set_breakpoints(
            source_path=str(self.fixture_file),
            breakpoints=[SourceBreakpoint(line=self.breakpoint_line)],
        )

        stopped_event = asyncio.Event()
        terminated_event = asyncio.Event()
        stopped_thread_id: int | None = None

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            nonlocal stopped_thread_id
            if event_type == EventType.STOPPED:
                stopped_thread_id = data.get("thread_id")
                stopped_event.set()
            elif event_type == EventType.TERMINATED:
                terminated_event.set()

        adapter._event_callback = event_handler

        config = LaunchConfig(program=str(self.fixture_file))
        await adapter.launch(config)

        # Wait for breakpoint
        await asyncio.wait_for(stopped_event.wait(), timeout=10.0)

        assert stopped_thread_id is not None

        # Continue
        await adapter.continue_execution(stopped_thread_id)

        # Wait for termination
        await asyncio.wait_for(terminated_event.wait(), timeout=10.0)

        await adapter.terminate()
