"""Per-project breakpoint persistence."""

from pathlib import Path

from polybugger_mcp.config import settings
from polybugger_mcp.models.dap import SourceBreakpoint
from polybugger_mcp.persistence.storage import (
    atomic_write,
    project_id_from_path,
    safe_delete,
    safe_read,
)


class BreakpointStore:
    """Manages per-project breakpoint persistence.

    Breakpoints are stored in JSON files, one per project.
    The project is identified by a hash of its root path.
    """

    def __init__(self, base_dir: Path | None = None):
        """Initialize the breakpoint store.

        Args:
            base_dir: Directory for breakpoint storage (defaults to settings)
        """
        self.base_dir = base_dir or settings.breakpoints_dir

    def _get_path(self, project_root: Path) -> Path:
        """Get storage path for a project's breakpoints."""
        project_id = project_id_from_path(project_root)
        return self.base_dir / f"{project_id}.json"

    async def load(
        self,
        project_root: Path,
    ) -> dict[str, list[SourceBreakpoint]]:
        """Load all breakpoints for a project.

        Args:
            project_root: Path to project root

        Returns:
            Dict mapping file paths to breakpoint lists
        """
        path = self._get_path(project_root)
        data = await safe_read(path)

        if not data:
            return {}

        result: dict[str, list[SourceBreakpoint]] = {}
        for file_path, breakpoints in data.get("breakpoints", {}).items():
            result[file_path] = [SourceBreakpoint(**bp) for bp in breakpoints]

        return result

    async def save(
        self,
        project_root: Path,
        breakpoints: dict[str, list[SourceBreakpoint]],
    ) -> None:
        """Save all breakpoints for a project.

        Args:
            project_root: Path to project root
            breakpoints: Dict mapping file paths to breakpoint lists
        """
        path = self._get_path(project_root)

        # Filter out empty lists
        filtered_breakpoints = {
            file_path: [bp.model_dump() for bp in bps]
            for file_path, bps in breakpoints.items()
            if bps
        }

        # If no breakpoints, delete the file
        if not filtered_breakpoints:
            await safe_delete(path)
            return

        data = {
            "project_root": str(project_root),
            "breakpoints": filtered_breakpoints,
        }

        await atomic_write(path, data)

    async def update_file(
        self,
        project_root: Path,
        file_path: str,
        breakpoints: list[SourceBreakpoint],
    ) -> None:
        """Update breakpoints for a single file.

        Args:
            project_root: Path to project root
            file_path: Path to the source file
            breakpoints: New breakpoint list for this file
        """
        all_breakpoints = await self.load(project_root)

        if breakpoints:
            all_breakpoints[file_path] = breakpoints
        else:
            all_breakpoints.pop(file_path, None)

        await self.save(project_root, all_breakpoints)

    async def clear(self, project_root: Path) -> None:
        """Clear all breakpoints for a project.

        Args:
            project_root: Path to project root
        """
        path = self._get_path(project_root)
        await safe_delete(path)

    async def get_file_breakpoints(
        self,
        project_root: Path,
        file_path: str,
    ) -> list[SourceBreakpoint]:
        """Get breakpoints for a specific file.

        Args:
            project_root: Path to project root
            file_path: Path to the source file

        Returns:
            List of breakpoints for the file
        """
        all_breakpoints = await self.load(project_root)
        return all_breakpoints.get(file_path, [])
