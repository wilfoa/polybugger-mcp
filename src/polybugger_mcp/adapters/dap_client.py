"""Debug Adapter Protocol (DAP) client implementation."""

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from polybugger_mcp.core.exceptions import DAPError, DAPTimeoutError

logger = logging.getLogger(__name__)


class DAPClient:
    """Client for communicating via Debug Adapter Protocol.

    Handles the DAP message framing (Content-Length headers),
    request/response correlation, and event dispatching.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        event_callback: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the DAP client.

        Args:
            reader: Stream reader for incoming messages
            writer: Stream writer for outgoing messages
            event_callback: Async callback for events (event_type, body)
            timeout: Default timeout for requests in seconds
        """
        self._reader = reader
        self._writer = writer
        self._event_callback = event_callback
        self._timeout = timeout

        self._seq = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self._reader_task: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        """Start the message reader loop."""
        self._reader_task = asyncio.create_task(self._read_loop())

    async def stop(self) -> None:
        """Stop the client and cleanup."""
        self._closed = True

        if self._reader_task:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task

        # Cancel all pending requests
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

        self._writer.close()
        with contextlib.suppress(Exception):
            await self._writer.wait_closed()

    async def send_request(
        self,
        command: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send a DAP request and wait for response.

        Args:
            command: DAP command name
            arguments: Command arguments
            timeout: Request timeout (uses default if not specified)

        Returns:
            Response body dictionary

        Raises:
            DAPTimeoutError: If request times out
            DAPError: If request fails
        """
        async with self._lock:
            self._seq += 1
            seq = self._seq

        request = {
            "seq": seq,
            "type": "request",
            "command": command,
            "arguments": arguments or {},
        }

        future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self._pending[seq] = future

        try:
            await self._send_message(request)
            response = await asyncio.wait_for(future, timeout=timeout or self._timeout)

            if not response.get("success", False):
                raise DAPError(
                    code="DAP_REQUEST_FAILED",
                    message=response.get("message", "Unknown error"),
                    details=response,
                )

            body: dict[str, Any] = response.get("body", {})
            return body

        except asyncio.TimeoutError:
            raise DAPTimeoutError(command, timeout or self._timeout) from None

        finally:
            self._pending.pop(seq, None)

    async def _send_message(self, message: dict[str, Any]) -> None:
        """Send a DAP message with Content-Length header."""
        content = json.dumps(message)
        content_bytes = content.encode("utf-8")
        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"

        self._writer.write(header.encode("utf-8"))
        self._writer.write(content_bytes)
        await self._writer.drain()

        logger.debug(f"DAP >> {message.get('command', message.get('type'))}")

    async def _read_loop(self) -> None:
        """Read and dispatch incoming DAP messages."""
        while not self._closed:
            try:
                message = await self._read_message()
                if message is None:
                    break

                await self._handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._closed:
                    logger.error(f"DAP read error: {e}")

    async def _read_message(self) -> dict[str, Any] | None:
        """Read a single DAP message."""
        # Read headers
        headers: dict[str, str] = {}
        while True:
            line = await self._reader.readline()
            if not line:
                return None

            line_str = line.decode("utf-8").strip()
            if not line_str:
                break

            if ":" in line_str:
                key, value = line_str.split(":", 1)
                headers[key.strip()] = value.strip()

        # Read content
        content_length = int(headers.get("Content-Length", 0))
        if content_length == 0:
            return None

        content = await self._reader.readexactly(content_length)
        message: dict[str, Any] = json.loads(content.decode("utf-8"))

        logger.debug(
            f"DAP << {message.get('type')}:{message.get('command', message.get('event', ''))}"
        )

        return message

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming DAP message."""
        msg_type = message.get("type")

        if msg_type == "response":
            # Match response to pending request
            seq = message.get("request_seq")
            if seq is not None:
                future = self._pending.get(seq)
                if future and not future.done():
                    future.set_result(message)

        elif msg_type == "event":
            # Dispatch event to callback
            if self._event_callback:
                event_type = message.get("event", "")
                body = message.get("body", {})
                try:
                    await self._event_callback(event_type, body)
                except Exception as e:
                    logger.error(f"Event callback error: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected and running."""
        return not self._closed and self._reader_task is not None
