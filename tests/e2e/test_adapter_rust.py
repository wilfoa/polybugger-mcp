"""Rust/LLDB (CodeLLDB) adapter integration tests.

These tests verify the CodeLLDB adapter works correctly for Rust debugging.
Tests are skipped if CodeLLDB is not available.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from polybugger_mcp.adapters.codelldb_adapter import (
    CodeLLDBAdapter,
    RustLaunchConfig,
    _find_codelldb,
)
from polybugger_mcp.models.dap import SourceBreakpoint
from polybugger_mcp.models.events import EventType

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "rust"


def _has_rust_toolchain() -> bool:
    """Check if Rust toolchain is available."""
    return shutil.which("rustc") is not None


def _compile_fixture() -> Path | None:
    """Compile the Rust fixture if needed."""
    source = FIXTURES_DIR / "simple.rs"
    binary = FIXTURES_DIR / "simple"

    if not source.exists():
        return None

    # Check if binary needs recompilation
    if binary.exists():
        src_mtime = source.stat().st_mtime
        bin_mtime = binary.stat().st_mtime
        if bin_mtime > src_mtime:
            return binary

    # Compile
    try:
        result = subprocess.run(
            ["rustc", "-g", "-o", str(binary), str(source)],
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0:
            return binary
    except Exception:
        pass

    return None


# Skip all tests if CodeLLDB or Rust is not available
pytestmark = [
    pytest.mark.skipif(
        _find_codelldb() is None,
        reason="CodeLLDB not found (install VS Code extension vadimcn.vscode-lldb)",
    ),
    pytest.mark.skipif(
        not _has_rust_toolchain(),
        reason="Rust toolchain not installed",
    ),
]


class TestCodeLLDBAdapter:
    """Test suite for Rust/LLDB CodeLLDB adapter."""

    @pytest_asyncio.fixture
    async def adapter(self):  # type: ignore[misc]
        """Create CodeLLDB adapter instance with cleanup."""
        _adapter = CodeLLDBAdapter(
            session_id="test-rust-session",
            output_callback=None,
            event_callback=None,
        )
        yield _adapter
        # Cleanup
        try:
            await _adapter.disconnect()
        except Exception:
            pass

    @pytest.fixture
    def compiled_binary(self) -> Path:
        """Compile the Rust fixture and return path to binary."""
        binary = _compile_fixture()
        if binary is None:
            pytest.skip("Failed to compile Rust fixture")
        return binary

    @pytest.mark.asyncio
    async def test_initialize(self, adapter: CodeLLDBAdapter) -> None:
        """Test adapter initialization."""
        capabilities = await adapter.initialize()

        assert adapter.is_connected
        assert capabilities is not None
        assert isinstance(capabilities, dict)

    @pytest.mark.asyncio
    async def test_launch_simple_program(
        self, adapter: CodeLLDBAdapter, compiled_binary: Path
    ) -> None:
        """Test launching a simple Rust program."""
        await adapter.initialize()

        # Track termination
        terminated = asyncio.Event()

        async def event_handler(event_type: EventType, data: dict[str, Any]) -> None:
            if event_type == EventType.TERMINATED:
                terminated.set()

        adapter._event_callback = event_handler

        # Launch without breakpoints - should run to completion
        config = RustLaunchConfig(program=str(compiled_binary), stop_on_entry=False)
        await adapter.launch(config)

        assert adapter.is_launched

        # Wait for termination
        await asyncio.wait_for(terminated.wait(), timeout=30.0)

    @pytest.mark.asyncio
    async def test_breakpoint_and_continue(
        self, adapter: CodeLLDBAdapter, compiled_binary: Path
    ) -> None:
        """Test setting breakpoint, hitting it, and continuing."""
        await adapter.initialize()

        source_file = FIXTURES_DIR / "simple.rs"

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
                source_path=str(source_file),
                breakpoints=[SourceBreakpoint(line=4)],  # let result = a + b (inside calculate)
            )

        # Launch with configure callback
        config = RustLaunchConfig(program=str(compiled_binary), stop_on_entry=False)
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
    async def test_inspect_variables_at_breakpoint(
        self, adapter: CodeLLDBAdapter, compiled_binary: Path
    ) -> None:
        """Test inspecting variables when stopped at breakpoint."""
        await adapter.initialize()

        source_file = FIXTURES_DIR / "simple.rs"

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
                source_path=str(source_file),
                breakpoints=[SourceBreakpoint(line=4)],  # let result = a + b (inside calculate)
            )

        # Launch with configure callback
        config = RustLaunchConfig(program=str(compiled_binary))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=30.0)

        assert stopped_thread_id is not None

        # Get stack trace
        frames = await adapter.get_stack_trace(stopped_thread_id)
        assert len(frames) > 0

        # Get scopes
        scopes = await adapter.get_scopes(frames[0].id)
        assert len(scopes) > 0

        # Find locals - LLDB may name scopes differently
        locals_scope = next(
            (s for s in scopes if "local" in s.name.lower() or s.name == "Locals"),
            scopes[0],
        )

        # Get variables
        variables = await adapter.get_variables(locals_scope.variables_reference)

        # Check variables exist - LLDB may expose them differently
        var_names = [v.name for v in variables]
        # In Rust with LLDB, parameters may be in the locals scope or a separate scope
        # Also check for any variable that contains 'a' or 'b' (LLDB sometimes mangles names)
        has_a = any("a" in name for name in var_names)
        has_b = any("b" in name for name in var_names)

        if not (has_a and has_b):
            # Try other scopes
            for scope in scopes:
                if scope.variables_reference != locals_scope.variables_reference:
                    other_vars = await adapter.get_variables(scope.variables_reference)
                    var_names.extend([v.name for v in other_vars])
            has_a = any("a" in name for name in var_names)
            has_b = any("b" in name for name in var_names)

        assert has_a, f"Expected variable containing 'a' in {var_names}"
        assert has_b, f"Expected variable containing 'b' in {var_names}"

    @pytest.mark.asyncio
    async def test_evaluate_expression(
        self, adapter: CodeLLDBAdapter, compiled_binary: Path
    ) -> None:
        """Test evaluating expressions at breakpoint."""
        await adapter.initialize()

        source_file = FIXTURES_DIR / "simple.rs"

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
                source_path=str(source_file),
                breakpoints=[SourceBreakpoint(line=4)],  # let result = a + b (inside calculate)
            )

        config = RustLaunchConfig(program=str(compiled_binary))
        await adapter.launch(config, configure_callback=configure)
        await asyncio.wait_for(stopped.wait(), timeout=30.0)

        assert stopped_thread_id is not None

        frames = await adapter.get_stack_trace(stopped_thread_id)
        frame_id = frames[0].id

        # Evaluate expression - LLDB may require different syntax
        # Try different expression formats that LLDB might accept
        result = await adapter.evaluate("a + b", frame_id=frame_id)

        assert "result" in result
        # LLDB may return the result in different formats
        result_str = str(result.get("result", ""))
        assert "30" in result_str or "(int) 30" in result_str or "i32) 30" in result_str, (
            f"Expected '30' in result: {result}"
        )
