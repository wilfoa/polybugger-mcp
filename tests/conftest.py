"""Global test fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

from dotenv import load_dotenv

# Load .env file for test API keys (e.g., ANTHROPIC_API_KEY for LLM tests)
# This must happen before any imports that instantiate Settings
load_dotenv()

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from polybugger_mcp.config import Settings
from polybugger_mcp.core.session import SessionManager
from polybugger_mcp.main import create_app
from polybugger_mcp.persistence.breakpoints import BreakpointStore
from polybugger_mcp.utils.output_buffer import OutputBuffer


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory."""
    data_dir = tmp_path / ".polybugger-mcp"
    data_dir.mkdir(parents=True)
    (data_dir / "breakpoints").mkdir()
    (data_dir / "sessions").mkdir()
    return data_dir


@pytest.fixture
def test_settings(tmp_data_dir: Path) -> Settings:
    """Create test settings with temporary data directory."""
    return Settings(
        host="127.0.0.1",
        port=5679,
        debug=False,
        max_sessions=10,
        data_dir=tmp_data_dir,
    )


@pytest_asyncio.fixture
async def breakpoint_store(tmp_data_dir: Path) -> BreakpointStore:
    """Create breakpoint store with temp directory."""
    return BreakpointStore(base_dir=tmp_data_dir / "breakpoints")


@pytest_asyncio.fixture
async def session_manager(
    breakpoint_store: BreakpointStore,
) -> AsyncGenerator[SessionManager, None]:
    """Create session manager for testing."""
    manager = SessionManager(breakpoint_store=breakpoint_store)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def output_buffer() -> OutputBuffer:
    """Create output buffer for testing."""
    return OutputBuffer(max_size=1024 * 1024)  # 1MB for tests


@pytest_asyncio.fixture
async def app():
    """Create FastAPI test app."""
    return create_app()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_script(tmp_path: Path) -> Path:
    """Create a simple test script."""
    script = tmp_path / "test_script.py"
    script.write_text(
        """
def add(a, b):
    result = a + b
    return result

def main():
    x = 10
    y = 20
    z = add(x, y)
    print(f"Result: {z}")
    return z

if __name__ == "__main__":
    main()
"""
    )
    return script


@pytest.fixture
def error_script(tmp_path: Path) -> Path:
    """Create a script that raises an exception."""
    script = tmp_path / "error_script.py"
    script.write_text(
        """
def divide(a, b):
    return a / b

def main():
    result = divide(10, 0)
    print(result)

if __name__ == "__main__":
    main()
"""
    )
    return script


@pytest.fixture
def loop_script(tmp_path: Path) -> Path:
    """Create a script with a loop for conditional breakpoint testing."""
    script = tmp_path / "loop_script.py"
    script.write_text(
        """
def process(items):
    total = 0
    for i, item in enumerate(items):
        total += item
        print(f"Processing item {i}: {item}, total: {total}")
    return total

def main():
    items = list(range(100))
    result = process(items)
    print(f"Final result: {result}")
    return result

if __name__ == "__main__":
    main()
"""
    )
    return script
