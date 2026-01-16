"""LLM-based E2E tests for debugging tools.

These tests use the Anthropic API to verify that an LLM can successfully
use our debugging tools to find and diagnose bugs in Python code.

Requirements:
    - ANTHROPIC_API_KEY environment variable must be set
    - Run with: pytest tests/e2e/test_llm_debugging.py -v

The tests are marked as slow and will be skipped if the API key is not set.
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest

# Skip all tests if anthropic is not installed or API key not set
anthropic = pytest.importorskip("anthropic")

from polybugger_mcp.core.session import SessionManager  # noqa: E402
from polybugger_mcp.models.dap import LaunchConfig, SourceBreakpoint  # noqa: E402
from polybugger_mcp.models.session import SessionConfig  # noqa: E402


def get_api_key() -> str | None:
    """Get Anthropic API key from environment."""
    return os.environ.get("ANTHROPIC_API_KEY")


# Skip if no API key
pytestmark = [
    pytest.mark.skipif(
        get_api_key() is None,
        reason="ANTHROPIC_API_KEY not set",
    ),
    pytest.mark.slow,
    pytest.mark.e2e,
]


# Define tool schemas for Claude
DEBUG_TOOLS = [
    {
        "name": "debug_list_languages",
        "description": "List supported programming languages for debugging.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "debug_create_session",
        "description": "Create a debug session. Returns session_id for other operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Project root path",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language (python, javascript, go, rust)",
                    "default": "python",
                },
                "name": {
                    "type": "string",
                    "description": "Session name (optional)",
                },
            },
            "required": ["project_root"],
        },
    },
    {
        "name": "debug_set_breakpoints",
        "description": "Set breakpoints in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "file_path": {"type": "string", "description": "Source file path"},
                "lines": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Line numbers",
                },
            },
            "required": ["session_id", "file_path", "lines"],
        },
    },
    {
        "name": "debug_launch",
        "description": "Launch program for debugging.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "program": {"type": "string", "description": "Script path"},
                "stop_on_entry": {
                    "type": "boolean",
                    "description": "Stop at first line",
                    "default": False,
                },
            },
            "required": ["session_id", "program"],
        },
    },
    {
        "name": "debug_poll_events",
        "description": "Poll for events (stopped, terminated). Use after launch/step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "timeout_seconds": {
                    "type": "number",
                    "description": "Wait time (default 5s)",
                    "default": 5.0,
                },
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "debug_get_stacktrace",
        "description": "Get call stack frames.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "format": {
                    "type": "string",
                    "description": "Output format: json or tui",
                    "default": "json",
                },
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "debug_get_scopes",
        "description": "Get scopes (locals, globals) for a frame.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "frame_id": {"type": "integer", "description": "Frame ID from stacktrace"},
            },
            "required": ["session_id", "frame_id"],
        },
    },
    {
        "name": "debug_get_variables",
        "description": "Get variables from a scope.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "variables_reference": {
                    "type": "integer",
                    "description": "Reference from scopes",
                },
            },
            "required": ["session_id", "variables_reference"],
        },
    },
    {
        "name": "debug_evaluate",
        "description": "Evaluate a Python expression.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "expression": {"type": "string", "description": "Expression to evaluate"},
                "frame_id": {"type": "integer", "description": "Frame ID (optional)"},
            },
            "required": ["session_id", "expression"],
        },
    },
    {
        "name": "debug_continue",
        "description": "Continue execution until next breakpoint or end.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "debug_step",
        "description": "Step execution: over (next line), into (enter function), out (exit).",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "mode": {
                    "type": "string",
                    "description": "Step mode: over, into, or out",
                    "enum": ["over", "into", "out"],
                },
            },
            "required": ["session_id", "mode"],
        },
    },
    {
        "name": "debug_terminate_session",
        "description": "Terminate session and clean up.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "report_findings",
        "description": "Report your debugging findings. Call this when you've identified the bug.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bug_location": {
                    "type": "string",
                    "description": "File and line number where bug is located",
                },
                "bug_description": {
                    "type": "string",
                    "description": "Description of what the bug is",
                },
                "root_cause": {
                    "type": "string",
                    "description": "Why the bug occurs",
                },
                "suggested_fix": {
                    "type": "string",
                    "description": "How to fix the bug",
                },
            },
            "required": ["bug_location", "bug_description", "root_cause", "suggested_fix"],
        },
    },
]


class DebugToolExecutor:
    """Executes debug tool calls against a real SessionManager."""

    def __init__(self, session_manager: SessionManager, project_root: Path):
        self.manager = session_manager
        self.project_root = project_root
        self.findings: dict[str, Any] | None = None

    async def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call and return the result."""
        if tool_name == "report_findings":
            self.findings = tool_input
            return {"status": "findings recorded", **tool_input}

        if tool_name == "debug_list_languages":
            from polybugger_mcp.adapters.factory import get_supported_languages

            return {
                "languages": get_supported_languages(),
                "default": "python",
            }

        if tool_name == "debug_create_session":
            config = SessionConfig(
                project_root=tool_input.get("project_root", str(self.project_root)),
                language=tool_input.get("language", "python"),
                name=tool_input.get("name"),
            )
            session = await self.manager.create_session(config)
            return {
                "session_id": session.id,
                "name": session.name,
                "language": session.language,
                "state": session.state.value,
            }

        if tool_name == "debug_set_breakpoints":
            session = await self.manager.get_session(tool_input["session_id"])
            breakpoints = [SourceBreakpoint(line=line) for line in tool_input["lines"]]
            result = await session.set_breakpoints(tool_input["file_path"], breakpoints)
            return {"breakpoints": [{"line": bp.line, "verified": bp.verified} for bp in result]}

        if tool_name == "debug_launch":
            session = await self.manager.get_session(tool_input["session_id"])
            config = LaunchConfig(
                program=tool_input["program"],
                stop_on_entry=tool_input.get("stop_on_entry", False),
            )
            await session.launch(config)
            return {"status": "launched", "state": session.state.value}

        if tool_name == "debug_poll_events":
            session = await self.manager.get_session(tool_input["session_id"])
            timeout = tool_input.get("timeout_seconds", 5.0)
            events = await session.event_queue.get_all(timeout=timeout)
            return {
                "events": [{"type": e.type.value, "data": e.data} for e in events],
                "session_state": session.state.value,
            }

        if tool_name == "debug_get_stacktrace":
            session = await self.manager.get_session(tool_input["session_id"])
            frames = await session.get_stack_trace()
            return {
                "frames": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "file": f.source.path if f.source else None,
                        "line": f.line,
                    }
                    for f in frames
                ]
            }

        if tool_name == "debug_get_scopes":
            session = await self.manager.get_session(tool_input["session_id"])
            scopes = await session.get_scopes(tool_input["frame_id"])
            return {
                "scopes": [
                    {
                        "name": s.name,
                        "variables_reference": s.variables_reference,
                    }
                    for s in scopes
                ]
            }

        if tool_name == "debug_get_variables":
            session = await self.manager.get_session(tool_input["session_id"])
            variables = await session.get_variables(tool_input["variables_reference"])
            return {
                "variables": [{"name": v.name, "value": v.value, "type": v.type} for v in variables]
            }

        if tool_name == "debug_evaluate":
            session = await self.manager.get_session(tool_input["session_id"])
            result = await session.evaluate(
                tool_input["expression"],
                tool_input.get("frame_id"),
            )
            return {
                "expression": tool_input["expression"],
                "result": result.get("result", ""),
                "type": result.get("type"),
            }

        if tool_name == "debug_continue":
            session = await self.manager.get_session(tool_input["session_id"])
            await session.continue_()
            return {"status": "continued"}

        if tool_name == "debug_step":
            session = await self.manager.get_session(tool_input["session_id"])
            mode = tool_input["mode"]
            if mode == "over":
                await session.step_over()
            elif mode == "into":
                await session.step_into()
            elif mode == "out":
                await session.step_out()
            return {"status": "stepping", "mode": mode}

        if tool_name == "debug_terminate_session":
            await self.manager.terminate_session(tool_input["session_id"])
            return {"status": "terminated"}

        return {"error": f"Unknown tool: {tool_name}"}


async def run_llm_debug_session(
    client: "anthropic.Anthropic",
    executor: DebugToolExecutor,
    system_prompt: str,
    user_prompt: str,
    max_iterations: int = 20,
) -> dict[str, Any]:
    """Run an LLM debugging session with tool use.

    Args:
        client: Anthropic client
        executor: Tool executor
        system_prompt: System instructions
        user_prompt: Initial user message
        max_iterations: Max tool call iterations

    Returns:
        Dict with conversation history and findings
    """
    messages = [{"role": "user", "content": user_prompt}]
    iterations = 0
    tool_calls = []

    while iterations < max_iterations:
        iterations += 1

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=DEBUG_TOOLS,
            messages=messages,
        )

        # Check for end conditions
        if response.stop_reason == "end_turn":
            # Claude finished without more tool calls
            break

        # Process response content
        assistant_content = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
                tool_uses.append(block)

        messages.append({"role": "assistant", "content": assistant_content})

        if not tool_uses:
            break

        # Execute tools and collect results
        tool_results = []
        for tool_use in tool_uses:
            tool_calls.append(
                {
                    "name": tool_use.name,
                    "input": tool_use.input,
                }
            )

            try:
                result = await executor.execute(tool_use.name, tool_use.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result),
                    }
                )
            except Exception as e:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps({"error": str(e)}),
                        "is_error": True,
                    }
                )

        messages.append({"role": "user", "content": tool_results})

        # Check if findings were reported
        if executor.findings is not None:
            break

    return {
        "iterations": iterations,
        "tool_calls": tool_calls,
        "findings": executor.findings,
        "messages": messages,
    }


class TestLLMDebugging:
    """Tests that verify an LLM can use our debugging tools effectively."""

    @pytest.fixture
    async def session_manager(self):
        """Create and start a session manager."""
        manager = SessionManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.fixture
    def anthropic_client(self):
        """Create Anthropic client."""
        return anthropic.Anthropic(api_key=get_api_key())

    @pytest.fixture
    def buggy_division_script(self, tmp_path: Path) -> Path:
        """Create a script with a division by zero bug."""
        script = tmp_path / "buggy_division.py"
        script.write_text('''
def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    total = sum(numbers)
    count = len(numbers)
    return total / count  # Bug: division by zero when list is empty


def process_data(data):
    """Process data and return averages."""
    results = []
    for group in data:
        avg = calculate_average(group)
        results.append(avg)
    return results


if __name__ == "__main__":
    # This will crash because one group is empty
    test_data = [
        [1, 2, 3],
        [],  # Empty list causes division by zero
        [4, 5, 6],
    ]
    result = process_data(test_data)
    print(f"Results: {result}")
''')
        return script

    @pytest.fixture
    def buggy_index_script(self, tmp_path: Path) -> Path:
        """Create a script with an index out of bounds bug."""
        script = tmp_path / "buggy_index.py"
        script.write_text('''
def find_max_pair_sum(numbers):
    """Find the maximum sum of adjacent pairs."""
    max_sum = float('-inf')
    for i in range(len(numbers)):  # Bug: should be range(len(numbers) - 1)
        pair_sum = numbers[i] + numbers[i + 1]  # IndexError on last iteration
        if pair_sum > max_sum:
            max_sum = pair_sum
    return max_sum


if __name__ == "__main__":
    test_numbers = [1, 5, 3, 9, 2]
    result = find_max_pair_sum(test_numbers)
    print(f"Max pair sum: {result}")
''')
        return script

    @pytest.mark.timeout(120)
    async def test_llm_finds_division_by_zero_bug(
        self,
        session_manager: SessionManager,
        anthropic_client: "anthropic.Anthropic",
        buggy_division_script: Path,
    ):
        """Test that LLM can find and diagnose a division by zero bug."""
        executor = DebugToolExecutor(
            session_manager,
            buggy_division_script.parent,
        )

        system_prompt = """You are an expert debugger. Use the debug tools to find bugs in Python code.

Workflow:
1. Create a debug session with debug_create_session
2. Set breakpoints at suspicious locations with debug_set_breakpoints
3. Launch the program with debug_launch
4. Poll for events with debug_poll_events to see when the program stops
5. Use debug_get_stacktrace, debug_get_scopes, debug_get_variables, and debug_evaluate to inspect state
6. Use debug_step or debug_continue to navigate through the code
7. When you find the bug, call report_findings with your analysis
8. Clean up with debug_terminate_session

Be systematic and thorough in your debugging."""

        user_prompt = f"""Debug this Python script that crashes with an error:

File: {buggy_division_script}

The script processes groups of numbers and calculates averages, but it crashes.
Find the bug, understand why it happens, and report your findings.

Start by creating a debug session and setting a breakpoint in the calculate_average function."""

        result = await run_llm_debug_session(
            anthropic_client,
            executor,
            system_prompt,
            user_prompt,
        )

        # Verify the LLM found the bug
        assert result["findings"] is not None, "LLM should report findings"
        findings = result["findings"]

        # Check that the bug was correctly identified
        assert (
            "division" in findings["bug_description"].lower()
            or "zero" in findings["bug_description"].lower()
        ), f"Should identify division by zero bug, got: {findings['bug_description']}"

        assert (
            "empty" in findings["root_cause"].lower()
            or "zero" in findings["root_cause"].lower()
            or "count" in findings["root_cause"].lower()
        ), f"Should identify empty list as root cause, got: {findings['root_cause']}"

        # Verify tools were used
        tool_names = [tc["name"] for tc in result["tool_calls"]]
        assert "debug_create_session" in tool_names
        assert "debug_launch" in tool_names
        assert "debug_poll_events" in tool_names

        print("\n=== LLM Debugging Results ===")
        print(f"Iterations: {result['iterations']}")
        print(f"Tool calls: {len(result['tool_calls'])}")
        print("\nFindings:")
        print(f"  Location: {findings['bug_location']}")
        print(f"  Description: {findings['bug_description']}")
        print(f"  Root cause: {findings['root_cause']}")
        print(f"  Suggested fix: {findings['suggested_fix']}")

    @pytest.mark.timeout(120)
    async def test_llm_finds_index_error_bug(
        self,
        session_manager: SessionManager,
        anthropic_client: "anthropic.Anthropic",
        buggy_index_script: Path,
    ):
        """Test that LLM can find and diagnose an index out of bounds bug."""
        executor = DebugToolExecutor(
            session_manager,
            buggy_index_script.parent,
        )

        system_prompt = """You are an expert debugger. Use the debug tools to find bugs in Python code.

Workflow:
1. Create a debug session with debug_create_session
2. Set breakpoints at suspicious locations with debug_set_breakpoints
3. Launch the program with debug_launch
4. Poll for events with debug_poll_events to see when the program stops
5. Use debug_get_stacktrace, debug_get_scopes, debug_get_variables, and debug_evaluate to inspect state
6. Use debug_step or debug_continue to navigate through the code
7. When you find the bug, call report_findings with your analysis
8. Clean up with debug_terminate_session

Be systematic and thorough in your debugging."""

        user_prompt = f"""Debug this Python script that crashes with an IndexError:

File: {buggy_index_script}

The script tries to find the maximum sum of adjacent pairs in a list but crashes.
Find the bug, understand why it happens, and report your findings.

Start by creating a debug session and setting a breakpoint in the find_max_pair_sum function."""

        result = await run_llm_debug_session(
            anthropic_client,
            executor,
            system_prompt,
            user_prompt,
        )

        # Verify the LLM found the bug
        assert result["findings"] is not None, "LLM should report findings"
        findings = result["findings"]

        # Check that the bug was correctly identified
        assert (
            "index" in findings["bug_description"].lower()
            or "bounds" in findings["bug_description"].lower()
            or "range" in findings["bug_description"].lower()
        ), f"Should identify index error bug, got: {findings['bug_description']}"

        # Verify tools were used
        tool_names = [tc["name"] for tc in result["tool_calls"]]
        assert "debug_create_session" in tool_names
        assert "debug_launch" in tool_names

        print("\n=== LLM Debugging Results ===")
        print(f"Iterations: {result['iterations']}")
        print(f"Tool calls: {len(result['tool_calls'])}")
        print("\nFindings:")
        print(f"  Location: {findings['bug_location']}")
        print(f"  Description: {findings['bug_description']}")
        print(f"  Root cause: {findings['root_cause']}")
        print(f"  Suggested fix: {findings['suggested_fix']}")

    @pytest.mark.timeout(60)
    async def test_llm_uses_language_selection(
        self,
        session_manager: SessionManager,
        anthropic_client: "anthropic.Anthropic",
        buggy_division_script: Path,
    ):
        """Test that LLM can list and select languages."""
        executor = DebugToolExecutor(
            session_manager,
            buggy_division_script.parent,
        )

        system_prompt = """You are a debugger assistant. First list the supported languages,
then create a Python debug session. Report what languages are available."""

        user_prompt = f"""I want to debug a Python script at {buggy_division_script}.

First, list the available languages using debug_list_languages.
Then create a debug session for Python.
Finally, report your findings about what languages are supported."""

        result = await run_llm_debug_session(
            anthropic_client,
            executor,
            system_prompt,
            user_prompt,
            max_iterations=5,
        )

        # Verify language tools were used
        tool_names = [tc["name"] for tc in result["tool_calls"]]
        assert "debug_list_languages" in tool_names, "Should call debug_list_languages"
        assert "debug_create_session" in tool_names, "Should create a session"

        # Check that session was created with correct language
        create_calls = [tc for tc in result["tool_calls"] if tc["name"] == "debug_create_session"]
        assert len(create_calls) > 0
        # Language might be explicitly "python" or omitted (default)

        print("\n=== Language Selection Test ===")
        print(f"Tool calls: {[tc['name'] for tc in result['tool_calls']]}")
