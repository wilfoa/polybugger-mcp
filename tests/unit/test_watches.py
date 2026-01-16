"""Tests for watch expression functionality."""

import pytest

from polybugger_mcp.core.session import Session


@pytest.fixture
def session(tmp_path):
    """Create a session for testing."""
    return Session(
        session_id="test_session",
        project_root=tmp_path,
        name="Test Session",
    )


class TestWatchExpressions:
    """Tests for watch expression management."""

    def test_add_watch(self, session: Session):
        """Test adding a watch expression."""
        result = session.add_watch("x + y")
        assert "x + y" in result
        assert len(result) == 1

    def test_add_duplicate_watch(self, session: Session):
        """Test adding duplicate watch expression is idempotent."""
        session.add_watch("x + y")
        result = session.add_watch("x + y")
        assert result.count("x + y") == 1
        assert len(result) == 1

    def test_add_multiple_watches(self, session: Session):
        """Test adding multiple watch expressions."""
        session.add_watch("x")
        session.add_watch("y")
        result = session.add_watch("z")
        assert len(result) == 3
        assert "x" in result
        assert "y" in result
        assert "z" in result

    def test_remove_watch(self, session: Session):
        """Test removing a watch expression."""
        session.add_watch("x")
        session.add_watch("y")
        result = session.remove_watch("x")
        assert "x" not in result
        assert "y" in result
        assert len(result) == 1

    def test_remove_nonexistent_watch(self, session: Session):
        """Test removing a nonexistent watch expression."""
        session.add_watch("x")
        result = session.remove_watch("nonexistent")
        assert "x" in result
        assert len(result) == 1

    def test_list_watches(self, session: Session):
        """Test listing watch expressions."""
        assert session.list_watches() == []
        session.add_watch("a")
        session.add_watch("b")
        watches = session.list_watches()
        assert len(watches) == 2
        assert "a" in watches
        assert "b" in watches

    def test_clear_watches(self, session: Session):
        """Test clearing all watch expressions."""
        session.add_watch("x")
        session.add_watch("y")
        session.clear_watches()
        assert session.list_watches() == []

    def test_watch_returns_copy(self, session: Session):
        """Test that list_watches returns a copy."""
        session.add_watch("x")
        watches = session.list_watches()
        watches.append("y")
        assert "y" not in session.list_watches()


class TestWatchPersistence:
    """Tests for watch expression persistence in session recovery."""

    def test_to_persisted_includes_watches(self, session: Session):
        """Test that persisted data includes watch expressions."""
        session.add_watch("foo")
        session.add_watch("bar.baz")

        persisted = session.to_persisted()
        assert persisted.watch_expressions == ["foo", "bar.baz"]

    def test_from_persisted_restores_watches(self, session: Session):
        """Test that recovered session has watch expressions."""
        session.add_watch("x * 2")
        session.add_watch("len(items)")

        persisted = session.to_persisted()
        recovered = Session.from_persisted(persisted)

        watches = recovered.list_watches()
        assert "x * 2" in watches
        assert "len(items)" in watches
