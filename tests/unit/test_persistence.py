"""Tests for persistence layer."""

from pathlib import Path

import pytest

from polybugger_mcp.models.dap import SourceBreakpoint
from polybugger_mcp.persistence.breakpoints import BreakpointStore
from polybugger_mcp.persistence.storage import (
    atomic_write,
    project_id_from_path,
    safe_delete,
    safe_read,
)


class TestStorageFunctions:
    """Tests for storage utility functions."""

    def test_project_id_from_path_consistent(self, tmp_path: Path) -> None:
        """Test that project ID is consistent for same path."""
        project = tmp_path / "my_project"
        project.mkdir()

        id1 = project_id_from_path(project)
        id2 = project_id_from_path(project)

        assert id1 == id2
        assert len(id1) == 16

    def test_project_id_from_path_different_for_different_paths(self, tmp_path: Path) -> None:
        """Test that different paths get different IDs."""
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        id1 = project_id_from_path(project1)
        id2 = project_id_from_path(project2)

        assert id1 != id2

    @pytest.mark.asyncio
    async def test_atomic_write_and_safe_read(self, tmp_path: Path) -> None:
        """Test atomic write and safe read."""
        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        await atomic_write(file_path, data)
        result = await safe_read(file_path)

        assert result == data

    @pytest.mark.asyncio
    async def test_safe_read_nonexistent_file(self, tmp_path: Path) -> None:
        """Test reading a file that doesn't exist."""
        file_path = tmp_path / "nonexistent.json"

        result = await safe_read(file_path)

        assert result is None

    @pytest.mark.asyncio
    async def test_safe_delete_existing_file(self, tmp_path: Path) -> None:
        """Test deleting an existing file."""
        file_path = tmp_path / "test.json"
        file_path.write_text("{}")

        result = await safe_delete(file_path)

        assert result is True
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_safe_delete_nonexistent_file(self, tmp_path: Path) -> None:
        """Test deleting a file that doesn't exist."""
        file_path = tmp_path / "nonexistent.json"

        result = await safe_delete(file_path)

        assert result is False

    @pytest.mark.asyncio
    async def test_atomic_write_creates_directories(self, tmp_path: Path) -> None:
        """Test that atomic write creates parent directories."""
        file_path = tmp_path / "nested" / "dir" / "test.json"

        await atomic_write(file_path, {"test": True})

        assert file_path.exists()


class TestBreakpointStore:
    """Tests for BreakpointStore class."""

    @pytest.mark.asyncio
    async def test_save_and_load_breakpoints(
        self, breakpoint_store: BreakpointStore, tmp_path: Path
    ) -> None:
        """Test saving and loading breakpoints."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        breakpoints = {
            "/path/to/file.py": [
                SourceBreakpoint(line=10),
                SourceBreakpoint(line=20, condition="x > 5"),
            ],
            "/path/to/other.py": [
                SourceBreakpoint(line=5),
            ],
        }

        await breakpoint_store.save(project_root, breakpoints)
        loaded = await breakpoint_store.load(project_root)

        assert len(loaded) == 2
        assert len(loaded["/path/to/file.py"]) == 2
        assert len(loaded["/path/to/other.py"]) == 1
        assert loaded["/path/to/file.py"][0].line == 10
        assert loaded["/path/to/file.py"][1].condition == "x > 5"

    @pytest.mark.asyncio
    async def test_load_nonexistent_project(
        self, breakpoint_store: BreakpointStore, tmp_path: Path
    ) -> None:
        """Test loading breakpoints for a project with no saved data."""
        project_root = tmp_path / "new_project"
        project_root.mkdir()

        loaded = await breakpoint_store.load(project_root)

        assert loaded == {}

    @pytest.mark.asyncio
    async def test_update_file_breakpoints(
        self, breakpoint_store: BreakpointStore, tmp_path: Path
    ) -> None:
        """Test updating breakpoints for a single file."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initial save
        await breakpoint_store.save(
            project_root,
            {"/path/to/file.py": [SourceBreakpoint(line=10)]},
        )

        # Update single file
        await breakpoint_store.update_file(
            project_root,
            "/path/to/file.py",
            [SourceBreakpoint(line=20), SourceBreakpoint(line=30)],
        )

        loaded = await breakpoint_store.load(project_root)

        assert len(loaded["/path/to/file.py"]) == 2
        assert loaded["/path/to/file.py"][0].line == 20

    @pytest.mark.asyncio
    async def test_clear_breakpoints(
        self, breakpoint_store: BreakpointStore, tmp_path: Path
    ) -> None:
        """Test clearing all breakpoints for a project."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        await breakpoint_store.save(
            project_root,
            {"/path/to/file.py": [SourceBreakpoint(line=10)]},
        )

        await breakpoint_store.clear(project_root)
        loaded = await breakpoint_store.load(project_root)

        assert loaded == {}

    @pytest.mark.asyncio
    async def test_get_file_breakpoints(
        self, breakpoint_store: BreakpointStore, tmp_path: Path
    ) -> None:
        """Test getting breakpoints for a specific file."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        await breakpoint_store.save(
            project_root,
            {
                "/path/to/file.py": [SourceBreakpoint(line=10)],
                "/path/to/other.py": [SourceBreakpoint(line=20)],
            },
        )

        breakpoints = await breakpoint_store.get_file_breakpoints(project_root, "/path/to/file.py")

        assert len(breakpoints) == 1
        assert breakpoints[0].line == 10

    @pytest.mark.asyncio
    async def test_get_file_breakpoints_nonexistent(
        self, breakpoint_store: BreakpointStore, tmp_path: Path
    ) -> None:
        """Test getting breakpoints for a file with no breakpoints."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        breakpoints = await breakpoint_store.get_file_breakpoints(
            project_root, "/path/to/nonexistent.py"
        )

        assert breakpoints == []
