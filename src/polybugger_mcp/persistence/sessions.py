"""Session persistence for recovery after server restart."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from polybugger_mcp.config import settings
from polybugger_mcp.persistence.storage import (
    atomic_write,
    list_json_files,
    safe_delete,
    safe_read,
)

logger = logging.getLogger(__name__)


class PersistedSession(BaseModel):
    """Session data persisted for recovery."""

    id: str
    name: str
    project_root: str
    state: str
    language: str = "python"  # Programming language for debug adapter
    created_at: datetime
    last_activity: datetime
    breakpoints: dict[str, list[dict[str, Any]]]
    watch_expressions: list[str] = []

    # Recovery metadata
    saved_at: datetime
    server_shutdown: bool = False  # True if saved during graceful shutdown


class SessionStore:
    """Manages session persistence for recovery.

    Sessions are persisted:
    - Periodically during operation (for crash recovery)
    - During graceful shutdown (for restart recovery)

    On startup, persisted sessions are loaded and can be used to:
    - Inform clients about previous session state
    - Restore breakpoints and watch expressions
    - Allow clients to create new sessions with previous settings
    """

    def __init__(self, base_dir: Path | None = None):
        """Initialize the session store.

        Args:
            base_dir: Directory for session storage (defaults to settings)
        """
        self.base_dir = base_dir or settings.sessions_dir

    def _get_path(self, session_id: str) -> Path:
        """Get storage path for a session."""
        return self.base_dir / f"{session_id}.json"

    async def save(self, session_data: PersistedSession) -> None:
        """Save session data for recovery.

        Args:
            session_data: Session data to persist
        """
        path = self._get_path(session_data.id)
        data = session_data.model_dump(mode="json")
        await atomic_write(path, data)
        logger.debug(f"Saved session {session_data.id} for recovery")

    async def load(self, session_id: str) -> PersistedSession | None:
        """Load persisted session data.

        Args:
            session_id: Session ID to load

        Returns:
            PersistedSession if found, None otherwise
        """
        path = self._get_path(session_id)
        data = await safe_read(path)

        if not data:
            return None

        try:
            return PersistedSession(**data)
        except Exception as e:
            logger.warning(f"Failed to parse session {session_id}: {e}")
            return None

    async def delete(self, session_id: str) -> bool:
        """Delete persisted session data.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._get_path(session_id)
        result = await safe_delete(path)
        if result:
            logger.debug(f"Deleted persisted session {session_id}")
        return result

    async def list_all(self) -> list[PersistedSession]:
        """List all persisted sessions.

        Returns:
            List of all persisted sessions
        """
        sessions: list[PersistedSession] = []
        files = await list_json_files(self.base_dir)

        for file_path in files:
            data = await safe_read(file_path)
            if data:
                try:
                    sessions.append(PersistedSession(**data))
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")

        return sessions

    async def cleanup_old(self, max_age_hours: int = 24) -> int:
        """Remove sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(timezone.utc)
        cleaned = 0

        sessions = await self.list_all()
        for session in sessions:
            age_hours = (now - session.saved_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                await self.delete(session.id)
                cleaned += 1
                logger.info(f"Cleaned up old session {session.id} (age: {age_hours:.1f}h)")

        return cleaned
