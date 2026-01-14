"""Event queue for debug events."""

import asyncio
import contextlib
from datetime import datetime, timezone
from typing import Any

from python_debugger_mcp.models.events import DebugEvent, EventType


class EventQueue:
    """Thread-safe event queue for a session.

    Events are stored in a queue and can be retrieved via polling.
    A history of recent events is also maintained for debugging.
    """

    def __init__(self, max_size: int = 1000, max_history: int = 100):
        """Initialize the event queue.

        Args:
            max_size: Maximum events in queue before dropping oldest
            max_history: Number of events to keep in history
        """
        self._queue: asyncio.Queue[DebugEvent] = asyncio.Queue(maxsize=max_size)
        self._history: list[DebugEvent] = []
        self._max_history = max_history
        self._event_counter = 0

    async def put(self, event_type: EventType, data: dict[str, Any]) -> None:
        """Add an event to the queue.

        Args:
            event_type: Type of event
            data: Event data payload
        """
        event = DebugEvent(
            type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data,
        )

        # Try to put in queue, drop oldest if full
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            with contextlib.suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()
            self._queue.put_nowait(event)

        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self._event_counter += 1

    async def get(self, timeout: float | None = None) -> DebugEvent | None:
        """Get next event, optionally with timeout.

        Args:
            timeout: Maximum seconds to wait for an event

        Returns:
            Next event or None if timeout/empty
        """
        try:
            if timeout:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return self._queue.get_nowait()
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

    async def get_all(self, timeout: float | None = None) -> list[DebugEvent]:
        """Get all pending events.

        If timeout is specified and no events are pending, waits up to
        timeout seconds for at least one event (long-polling).

        Args:
            timeout: Seconds to wait if queue is empty (long-polling)

        Returns:
            List of all pending events
        """
        events: list[DebugEvent] = []

        # First, drain any existing events
        while True:
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        # If no events and timeout specified, wait for one
        if not events and timeout:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                events.append(event)
                # Drain any additional events that arrived
                while True:
                    try:
                        events.append(self._queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break
            except asyncio.TimeoutError:
                pass

        return events

    def clear(self) -> None:
        """Clear all pending events."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._history.clear()
        self._event_counter = 0

    @property
    def pending_count(self) -> int:
        """Number of events waiting in queue."""
        return self._queue.qsize()

    @property
    def total_events(self) -> int:
        """Total events processed."""
        return self._event_counter

    @property
    def history(self) -> list[DebugEvent]:
        """Recent event history (read-only copy)."""
        return list(self._history)
