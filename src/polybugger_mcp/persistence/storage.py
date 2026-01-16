"""Atomic file storage operations."""

import contextlib
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from polybugger_mcp.core.exceptions import PersistenceError


def project_id_from_path(project_root: Path) -> str:
    """Generate stable ID from project path.

    Args:
        project_root: Path to project root

    Returns:
        16-character hex string derived from path hash
    """
    normalized = str(project_root.resolve())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


async def atomic_write(path: Path, data: dict[str, Any]) -> None:
    """Write JSON data atomically using temp file + rename.

    This ensures that the file is either fully written or not written at all,
    preventing corruption from partial writes.

    Args:
        path: Target file path
        data: Dictionary to serialize as JSON
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(".tmp")

    try:
        content = json.dumps(data, indent=2, default=str)

        async with aiofiles.open(temp_path, "w") as f:
            await f.write(content)
            await f.flush()
            # Ensure data is written to disk
            os.fsync(f.fileno())

        # Atomic rename (on POSIX systems)
        await aiofiles.os.rename(temp_path, path)

    except Exception as e:
        # Cleanup temp file on error
        with contextlib.suppress(FileNotFoundError):
            await aiofiles.os.remove(temp_path)

        raise PersistenceError(
            code="WRITE_FAILED",
            message=f"Failed to write {path}: {e}",
            details={"path": str(path), "error": str(e)},
        )


async def safe_read(path: Path) -> dict[str, Any] | None:
    """Read JSON data, returning None if file doesn't exist.

    Args:
        path: File path to read

    Returns:
        Parsed JSON data or None if file doesn't exist
    """
    try:
        async with aiofiles.open(path) as f:
            content = await f.read()
            data: dict[str, Any] = json.loads(content)
            return data
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        raise PersistenceError(
            code="INVALID_JSON",
            message=f"Invalid JSON in {path}: {e}",
            details={"path": str(path), "error": str(e)},
        )


async def safe_delete(path: Path) -> bool:
    """Delete a file if it exists.

    Args:
        path: File path to delete

    Returns:
        True if file was deleted, False if it didn't exist
    """
    try:
        await aiofiles.os.remove(path)
        return True
    except FileNotFoundError:
        return False


async def list_json_files(directory: Path) -> list[Path]:
    """List all .json files in a directory.

    Args:
        directory: Directory to scan

    Returns:
        List of paths to JSON files
    """
    if not directory.exists():
        return []

    return [directory / name for name in os.listdir(directory) if name.endswith(".json")]
