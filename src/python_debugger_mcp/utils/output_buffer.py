"""Ring buffer for output capture with size limits."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class OutputLine:
    """Single line of output."""

    line_number: int
    category: str  # "stdout", "stderr", "console"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OutputPage:
    """Paginated output response."""

    lines: list[OutputLine]
    offset: int
    limit: int
    total: int
    has_more: bool
    truncated: bool  # True if buffer limit was reached


class OutputBuffer:
    """Ring buffer for capturing debug output with size limits.

    When the buffer exceeds max_size, oldest entries are dropped
    to make room for new entries.
    """

    def __init__(self, max_size: int = 50 * 1024 * 1024):
        """Initialize the output buffer.

        Args:
            max_size: Maximum buffer size in bytes (default 50MB)
        """
        self.max_size = max_size
        self._entries: deque[OutputLine] = deque()
        self._current_size: int = 0
        self._total_dropped: int = 0
        self._line_counter: int = 0

    def append(self, category: str, content: str) -> None:
        """Add output to the buffer.

        Args:
            category: Output category ("stdout", "stderr", "console")
            content: The output content
        """
        entry_size = len(content.encode("utf-8"))

        # Drop oldest entries if needed to make room
        while self._current_size + entry_size > self.max_size and self._entries:
            dropped = self._entries.popleft()
            self._current_size -= len(dropped.content.encode("utf-8"))
            self._total_dropped += 1

        self._line_counter += 1
        entry = OutputLine(
            line_number=self._line_counter,
            category=category,
            content=content,
        )

        self._entries.append(entry)
        self._current_size += entry_size

    def get_page(
        self,
        offset: int = 0,
        limit: int = 1000,
        category: str | None = None,
    ) -> OutputPage:
        """Get a page of output.

        Args:
            offset: Starting index
            limit: Maximum number of entries to return
            category: Filter by category (optional)

        Returns:
            OutputPage with the requested entries
        """
        # Filter by category if specified
        if category:
            entries = [e for e in self._entries if e.category == category]
        else:
            entries = list(self._entries)

        total = len(entries)
        page_entries = entries[offset : offset + limit]

        return OutputPage(
            lines=page_entries,
            offset=offset,
            limit=limit,
            total=total,
            has_more=(offset + limit) < total,
            truncated=self._total_dropped > 0,
        )

    def get_since(self, line_number: int, limit: int = 1000) -> OutputPage:
        """Get output since a specific line number.

        Args:
            line_number: Get entries after this line number
            limit: Maximum number of entries to return

        Returns:
            OutputPage with entries after line_number
        """
        entries = [e for e in self._entries if e.line_number > line_number]
        page_entries = entries[:limit]

        return OutputPage(
            lines=page_entries,
            offset=0,
            limit=limit,
            total=len(entries),
            has_more=len(entries) > limit,
            truncated=self._total_dropped > 0,
        )

    def clear(self) -> None:
        """Clear all output."""
        self._entries.clear()
        self._current_size = 0
        self._total_dropped = 0
        self._line_counter = 0

    @property
    def size(self) -> int:
        """Current buffer size in bytes."""
        return self._current_size

    @property
    def total_lines(self) -> int:
        """Total lines currently in buffer."""
        return len(self._entries)

    @property
    def dropped_lines(self) -> int:
        """Number of lines dropped due to size limit."""
        return self._total_dropped

    @property
    def last_line_number(self) -> int:
        """Line number of the last entry (for cursor-based pagination)."""
        return self._line_counter
