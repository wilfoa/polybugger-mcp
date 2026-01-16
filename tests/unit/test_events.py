"""Tests for the events module."""

import asyncio

import pytest

from polybugger_mcp.core.events import EventQueue
from polybugger_mcp.models.events import DebugEvent, EventType


class TestEventQueue:
    """Tests for the EventQueue class."""

    @pytest.fixture
    def event_queue(self):
        """Create an event queue for testing."""
        return EventQueue(max_size=10)

    @pytest.mark.asyncio
    async def test_put_and_get(self, event_queue):
        """Test putting and getting events."""
        await event_queue.put(EventType.STOPPED, {"reason": "breakpoint"})

        events = await event_queue.get_all(timeout=1.0)

        assert len(events) == 1
        assert events[0].type == EventType.STOPPED
        assert events[0].data["reason"] == "breakpoint"

    @pytest.mark.asyncio
    async def test_put_multiple_events(self, event_queue):
        """Test putting multiple events."""
        await event_queue.put(EventType.STOPPED, {})
        await event_queue.put(EventType.CONTINUED, {})
        await event_queue.put(EventType.OUTPUT, {"output": "test"})

        events = await event_queue.get_all(timeout=1.0)

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_get_all_timeout(self, event_queue):
        """Test get_all with timeout when no events."""
        events = await event_queue.get_all(timeout=0.1)

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_all_waits_for_first(self, event_queue):
        """Test that get_all waits for at least one event."""

        async def add_event_later():
            await asyncio.sleep(0.1)
            await event_queue.put(EventType.STOPPED, {})

        task = asyncio.create_task(add_event_later())

        events = await event_queue.get_all(timeout=1.0)

        assert len(events) == 1
        await task

    @pytest.mark.asyncio
    async def test_queue_overflow_drops_oldest(self):
        """Test that queue drops oldest events when full."""
        queue = EventQueue(max_size=3)

        # Fill the queue beyond capacity
        for i in range(5):
            await queue.put(EventType.OUTPUT, {"index": i})

        events = await queue.get_all(timeout=0.1)

        # Should have the last 3 events
        assert len(events) == 3
        # The oldest should have been dropped
        indices = [e.data["index"] for e in events]
        assert indices == [2, 3, 4]

    @pytest.mark.asyncio
    async def test_clear(self, event_queue):
        """Test clearing the queue."""
        await event_queue.put(EventType.STOPPED, {})
        await event_queue.put(EventType.CONTINUED, {})

        event_queue.clear()

        events = await event_queue.get_all(timeout=0.1)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_pending_count(self, event_queue):
        """Test getting pending event count."""
        assert event_queue.pending_count == 0

        await event_queue.put(EventType.STOPPED, {})
        assert event_queue.pending_count == 1

        await event_queue.put(EventType.CONTINUED, {})
        assert event_queue.pending_count == 2

    @pytest.mark.asyncio
    async def test_total_events(self, event_queue):
        """Test total events counter."""
        assert event_queue.total_events == 0

        await event_queue.put(EventType.STOPPED, {})
        assert event_queue.total_events == 1

        await event_queue.put(EventType.CONTINUED, {})
        assert event_queue.total_events == 2

    @pytest.mark.asyncio
    async def test_history(self, event_queue):
        """Test event history."""
        await event_queue.put(EventType.STOPPED, {"reason": "test"})

        history = event_queue.history
        assert len(history) == 1
        assert history[0].type == EventType.STOPPED

    @pytest.mark.asyncio
    async def test_get_single_event(self, event_queue):
        """Test getting a single event."""
        await event_queue.put(EventType.STOPPED, {})

        event = await event_queue.get(timeout=1.0)

        assert event is not None
        assert event.type == EventType.STOPPED

    @pytest.mark.asyncio
    async def test_get_single_event_timeout(self, event_queue):
        """Test get with timeout when no events."""
        event = await event_queue.get(timeout=0.1)
        assert event is None

    @pytest.mark.asyncio
    async def test_get_single_event_no_timeout(self, event_queue):
        """Test get without timeout when no events."""
        event = await event_queue.get()
        assert event is None


class TestDebugEvent:
    """Tests for the DebugEvent model."""

    def test_event_creation(self):
        """Test creating a debug event."""
        from datetime import datetime, timezone

        event = DebugEvent(
            type=EventType.STOPPED,
            timestamp=datetime.now(timezone.utc),
            data={"reason": "breakpoint"},
        )

        assert event.type == EventType.STOPPED
        assert event.data["reason"] == "breakpoint"
        assert event.timestamp is not None

    def test_event_types(self):
        """Test all event types can be created."""
        from datetime import datetime, timezone

        for event_type in EventType:
            event = DebugEvent(
                type=event_type,
                timestamp=datetime.now(timezone.utc),
                data={},
            )
            assert event.type == event_type

    def test_event_default_data(self):
        """Test event with default data."""
        from datetime import datetime, timezone

        event = DebugEvent(
            type=EventType.STOPPED,
            timestamp=datetime.now(timezone.utc),
        )
        assert event.data == {}
