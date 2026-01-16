"""Tests for output buffer."""

from polybugger_mcp.utils.output_buffer import OutputBuffer


class TestOutputBuffer:
    """Tests for OutputBuffer class."""

    def test_append_and_retrieve(self, output_buffer: OutputBuffer) -> None:
        """Test appending and retrieving output."""
        output_buffer.append("stdout", "Hello, World!\n")
        output_buffer.append("stderr", "Warning!\n")

        page = output_buffer.get_page()

        assert len(page.lines) == 2
        assert page.lines[0].content == "Hello, World!\n"
        assert page.lines[0].category == "stdout"
        assert page.lines[1].content == "Warning!\n"
        assert page.lines[1].category == "stderr"

    def test_line_numbers_are_sequential(self, output_buffer: OutputBuffer) -> None:
        """Test that line numbers are sequential."""
        for i in range(5):
            output_buffer.append("stdout", f"Line {i}\n")

        page = output_buffer.get_page()

        for i, line in enumerate(page.lines, start=1):
            assert line.line_number == i

    def test_category_filtering(self, output_buffer: OutputBuffer) -> None:
        """Test filtering by category."""
        output_buffer.append("stdout", "stdout 1\n")
        output_buffer.append("stderr", "stderr 1\n")
        output_buffer.append("stdout", "stdout 2\n")

        stdout_page = output_buffer.get_page(category="stdout")
        stderr_page = output_buffer.get_page(category="stderr")

        assert len(stdout_page.lines) == 2
        assert len(stderr_page.lines) == 1
        assert all(line.category == "stdout" for line in stdout_page.lines)
        assert all(line.category == "stderr" for line in stderr_page.lines)

    def test_pagination(self, output_buffer: OutputBuffer) -> None:
        """Test pagination with offset and limit."""
        for i in range(10):
            output_buffer.append("stdout", f"Line {i}\n")

        # Get first 3
        page1 = output_buffer.get_page(offset=0, limit=3)
        assert len(page1.lines) == 3
        assert page1.has_more is True
        assert page1.offset == 0
        assert page1.limit == 3
        assert page1.total == 10

        # Get next 3
        page2 = output_buffer.get_page(offset=3, limit=3)
        assert len(page2.lines) == 3
        assert page2.has_more is True

        # Get last 4
        page3 = output_buffer.get_page(offset=6, limit=10)
        assert len(page3.lines) == 4
        assert page3.has_more is False

    def test_get_since_line_number(self, output_buffer: OutputBuffer) -> None:
        """Test getting lines since a specific line number."""
        for i in range(10):
            output_buffer.append("stdout", f"Line {i}\n")

        # Get lines after line 5
        page = output_buffer.get_since(line_number=5, limit=100)

        assert len(page.lines) == 5
        assert page.lines[0].line_number == 6

    def test_ring_buffer_drops_old_entries(self) -> None:
        """Test that old entries are dropped when buffer is full."""
        # Create small buffer (100 bytes)
        buffer = OutputBuffer(max_size=100)

        # Add entries that exceed buffer size
        for i in range(20):
            buffer.append("stdout", f"Line {i}: some content here\n")

        # Buffer should have dropped old entries
        assert buffer.dropped_lines > 0
        assert buffer.size <= 100
        assert buffer.total_lines < 20

    def test_truncated_flag(self) -> None:
        """Test truncated flag when entries are dropped."""
        buffer = OutputBuffer(max_size=50)

        # Add entries that exceed buffer
        for i in range(10):
            buffer.append("stdout", f"Line {i}\n")

        page = buffer.get_page()
        assert page.truncated is True

    def test_clear(self, output_buffer: OutputBuffer) -> None:
        """Test clearing the buffer."""
        for i in range(5):
            output_buffer.append("stdout", f"Line {i}\n")

        output_buffer.clear()

        assert output_buffer.total_lines == 0
        assert output_buffer.size == 0
        assert output_buffer.dropped_lines == 0
        assert output_buffer.last_line_number == 0

    def test_properties(self, output_buffer: OutputBuffer) -> None:
        """Test buffer properties."""
        output_buffer.append("stdout", "Hello\n")
        output_buffer.append("stderr", "World\n")

        assert output_buffer.total_lines == 2
        assert output_buffer.size > 0
        assert output_buffer.last_line_number == 2
        assert output_buffer.dropped_lines == 0

    def test_timestamps(self, output_buffer: OutputBuffer) -> None:
        """Test that entries have timestamps."""
        output_buffer.append("stdout", "Test\n")

        page = output_buffer.get_page()

        assert page.lines[0].timestamp is not None
