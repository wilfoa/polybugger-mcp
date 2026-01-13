"""Tests for session recovery functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from opencode_debugger.core.session import Session
from opencode_debugger.models.dap import SourceBreakpoint
from opencode_debugger.persistence.sessions import PersistedSession, SessionStore


@pytest.fixture
def session_store(tmp_path):
    """Create a session store for testing."""
    return SessionStore(base_dir=tmp_path / "sessions")


@pytest.fixture
def sample_session(tmp_path):
    """Create a sample session with data."""
    session = Session(
        session_id="sess_abc123",
        project_root=tmp_path / "project",
        name="Test Session",
    )
    
    # Add some breakpoints
    session._breakpoints = {
        "/path/to/file.py": [
            SourceBreakpoint(line=10),
            SourceBreakpoint(line=20, condition="x > 5"),
        ],
        "/path/to/other.py": [
            SourceBreakpoint(line=5),
        ],
    }
    
    # Add watch expressions
    session.add_watch("x + y")
    session.add_watch("len(items)")
    
    return session


class TestPersistedSession:
    """Tests for PersistedSession model."""

    def test_session_to_persisted(self, sample_session: Session):
        """Test converting session to persisted format."""
        persisted = sample_session.to_persisted()
        
        assert persisted.id == "sess_abc123"
        assert persisted.name == "Test Session"
        assert persisted.state == "created"
        assert len(persisted.breakpoints) == 2
        assert len(persisted.watch_expressions) == 2

    def test_session_to_persisted_shutdown_flag(self, sample_session: Session):
        """Test server_shutdown flag in persisted session."""
        persisted_normal = sample_session.to_persisted(server_shutdown=False)
        persisted_shutdown = sample_session.to_persisted(server_shutdown=True)
        
        assert not persisted_normal.server_shutdown
        assert persisted_shutdown.server_shutdown

    def test_session_from_persisted(self, sample_session: Session):
        """Test recovering session from persisted data."""
        persisted = sample_session.to_persisted()
        recovered = Session.from_persisted(persisted)
        
        assert recovered.id == sample_session.id
        assert recovered.name == sample_session.name
        assert str(recovered.project_root) == str(sample_session.project_root)
        
        # Check breakpoints restored
        assert len(recovered._breakpoints) == 2
        assert len(recovered._breakpoints["/path/to/file.py"]) == 2
        
        # Check watch expressions restored
        assert recovered.list_watches() == ["x + y", "len(items)"]


class TestSessionStore:
    """Tests for SessionStore persistence."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, session_store: SessionStore, sample_session: Session):
        """Test saving and loading a session."""
        persisted = sample_session.to_persisted()
        
        await session_store.save(persisted)
        loaded = await session_store.load(persisted.id)
        
        assert loaded is not None
        assert loaded.id == persisted.id
        assert loaded.name == persisted.name
        assert loaded.watch_expressions == persisted.watch_expressions

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, session_store: SessionStore):
        """Test loading a nonexistent session returns None."""
        loaded = await session_store.load("nonexistent_id")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete(self, session_store: SessionStore, sample_session: Session):
        """Test deleting a persisted session."""
        persisted = sample_session.to_persisted()
        await session_store.save(persisted)
        
        result = await session_store.delete(persisted.id)
        assert result is True
        
        loaded = await session_store.load(persisted.id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, session_store: SessionStore):
        """Test deleting a nonexistent session."""
        result = await session_store.delete("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_all(self, session_store: SessionStore, tmp_path):
        """Test listing all persisted sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = Session(
                session_id=f"sess_{i}",
                project_root=tmp_path / f"project_{i}",
                name=f"Session {i}",
            )
            sessions.append(session.to_persisted())
            await session_store.save(sessions[-1])
        
        all_sessions = await session_store.list_all()
        assert len(all_sessions) == 3
        ids = {s.id for s in all_sessions}
        assert ids == {"sess_0", "sess_1", "sess_2"}

    @pytest.mark.asyncio
    async def test_cleanup_old(self, session_store: SessionStore, tmp_path):
        """Test cleaning up old sessions."""
        # Create an old session
        old_session = Session(
            session_id="old_sess",
            project_root=tmp_path / "old",
            name="Old Session",
        )
        old_persisted = old_session.to_persisted()
        # Manually set saved_at to 48 hours ago
        old_persisted.saved_at = datetime.now(timezone.utc) - timedelta(hours=48)
        await session_store.save(old_persisted)
        
        # Create a new session
        new_session = Session(
            session_id="new_sess",
            project_root=tmp_path / "new",
            name="New Session",
        )
        await session_store.save(new_session.to_persisted())
        
        # Cleanup with 24 hour max age
        cleaned = await session_store.cleanup_old(max_age_hours=24)
        assert cleaned == 1
        
        # Old session should be gone
        assert await session_store.load("old_sess") is None
        # New session should still exist
        assert await session_store.load("new_sess") is not None
