"""TCP socket abstraction for sending and receiving messages.

Provides a high-level API over a TCP socket to send and receive messages as
objects.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Coroutine, Iterable
from typing import Any, Generic, Optional, Protocol, TypeVar

import pyairtouch.comms.log
from pyairtouch import comms

_LOGGER = pyairtouch.comms.log.getLogger(__name__)

_CONNECT_RETRY_DELAY = 2.0
"""Delay after which a connection attempt will be retried."""

_CONNECTION_MONITOR_INTERVAL = 180.0
"""Interval for checking in on the connection status.

This is low cost, so we do it quite frequently.
"""


class NotConnectedError(RuntimeError):
    """Raised when an attempt is made to use a socket that is not connected."""


class ConnectionSubscriber(Protocol):
    """Protocol for connection change subscribers."""

    def __call__(self, *, connected: bool) -> Awaitable[None]:
        """Connection state has changed.

        Args:
            connected: whether or not the socket is connected.
        """


MessageSubscriber = Callable[[comms.Hdr, comms.Message], Awaitable[None]]


class AirTouchSocket(Generic[comms.Hdr]):
    """A socket for communicating with an AirTouch system."""

    def __init__(
        self,
        host: str,
        port: int,
        registry: comms.MessageRegistry[comms.Hdr],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Initialise the AirTouch socket.

        Args:
            host: Host name or IP address for the AirTouch.
            port: Remote port number for the TCP connection.
            registry: Registry for message encoders and decoders.
            loop: Event loop for scheduling background tasks.
        """
        self.host = host
        self.port = port
        self._registry = registry
        self._loop = loop

        self.is_open = False
        self.is_connected = False

        self._background_tasks: set[asyncio.Task[Any]] = set()

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connection_monitor_task: Optional[asyncio.Task[None]] = None

        self._connection_subscribers: set[ConnectionSubscriber] = set()
        self._message_subscribers: set[MessageSubscriber[comms.Hdr]] = set()

    async def open_socket(self) -> None:
        """Open the socket to the AirTouch."""
        if not self.is_open:
            self._schedule(self._connect())
            self.is_open = True

    async def close(self) -> None:
        """Close the socket to the AirTouch."""
        if self.is_open:
            await self._disconnect()
            self.is_open = False

    async def send(self, message: comms.Message) -> None:
        """Send a message to the AirTouch.

        Raises:
            NotConnectedError if the socket is not connected.
        """
        message_encoder = self._registry.get_encoder(message.message_id)
        message_length = message_encoder.size(message)
        header = self._registry.header_factory.create_from_message(
            message, message_length
        )
        await self._write(header, message)

    async def send_with_header(self, header: comms.Hdr, message: comms.Message) -> None:
        """Send a message with a custom header to the AirTouch.

        Raises:
            NotConnectedError if the socket is not connected.
        """
        await self._write(header, message)

    def subscribe_on_connection_changed(self, subscriber: ConnectionSubscriber) -> None:
        """Subscribe to receive connection change notifications."""
        self._connection_subscribers.add(subscriber)

    def unsubscribe_on_connection_changed(
        self, subscriber: ConnectionSubscriber
    ) -> None:
        """Unsubscribe from receiving connection change notifications."""
        self._connection_subscribers.discard(subscriber)

    def subscribe_on_message_received(
        self, subscriber: MessageSubscriber[comms.Hdr]
    ) -> None:
        """Subscribe to receive notifications when a message is received."""
        self._message_subscribers.add(subscriber)

    def unsubcribe_on_message_received(
        self, subscriber: MessageSubscriber[comms.Hdr]
    ) -> None:
        """Unsubscribe from receiving notifications when a message is received."""
        self._message_subscribers.discard(subscriber)

    def _schedule(
        self, coro: Coroutine[Any, Any, Any], delay: Optional[float] = None
    ) -> None:
        """Schedule a co-routine to run in the background with an optional delay."""
        if delay:
            coro = _delay(coro, delay)

        task = asyncio.create_task(coro)
        # Store a reference to the task as per the create_task documentation.
        self._background_tasks.add(task)

        def discard_task(task: asyncio.Task[Any]) -> None:
            self._background_tasks.discard(task)
            with contextlib.suppress(asyncio.CancelledError):
                ex = task.exception()
                if ex:
                    _LOGGER.error(
                        "Unhandled exception in background task.", exc_info=ex
                    )

        task.add_done_callback(discard_task)

    async def _connect(self) -> None:
        if self.is_connected:
            _LOGGER.debug("_connect ignored. Already connected")
            return

        _LOGGER.debug("Attempting to open connection to %s:%d", self.host, self.port)
        try:
            self._reader, self._writer = await asyncio.open_connection(
                host=self.host, port=self.port
            )

            self.is_connected = True
            _LOGGER.debug("Connected to %s:%d", self.host, self.port)
            await self._notify_connection_changed(connected=self.is_connected)

            self._schedule(self._read())
            self._connection_monitor_task = await self._loop.create_task(
                self._connection_monitor()
            )
        except OSError:
            _LOGGER.debug("Unable to connect. Will try again later.")

        if not self.is_connected:
            # Connection failed, so retry after a small delay
            self._schedule(self._connect(), delay=_CONNECT_RETRY_DELAY)

    async def _disconnect(self) -> None:
        _LOGGER.debug("_disconnect: is_connected=%s", self.is_connected)
        if self._connection_monitor_task:
            self._connection_monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._connection_monitor_task

        if self._writer:
            self._writer.close()
            # wait_closed could raise an error if the socket has been closed by
            # the other side. This will already have been logged, so just
            # suppress it here.
            with contextlib.suppress(OSError):
                await self._writer.wait_closed()

        self.is_connected = False
        self._reader = None
        self._writer = None
        await self._notify_connection_changed(connected=self.is_connected)

    async def _reset_connection(self) -> None:
        """Resets the connection to the AirTouch.

        The connection is reset by disconnecting and re-connecting the
        underlying socket.
        """
        await self._disconnect()
        self._schedule(self._connect())

    async def _connection_monitor(self) -> None:
        """Helper co-routine to regularly check the connection status.

        If no messages are sent for a while, the socket may not raise a
        connection lost event. By regularly calling `drain()` we force a check
        for these connection lost events.
        """
        try:
            while True:  # Run until cancelled.
                # We don't care if this drifts.
                await asyncio.sleep(_CONNECTION_MONITOR_INTERVAL)
                if self._writer:
                    await self._writer.drain()
        except OSError as ex:
            _LOGGER.debug("Detected closed socket: %s", ex)
            await self._reset_connection()

    async def _read(self) -> None:
        """The main read loop for the AirTouch socket."""
        try:
            while self._reader:
                read_result = await self._read_one_message()
                if read_result:
                    header, message = read_result
                    await self._notify_message_received(header, message)
                else:
                    await self._reset_connection()

        except asyncio.IncompleteReadError:
            _LOGGER.debug("Socket closed")
            if self._writer and not self._writer.is_closing():
                _LOGGER.debug("Socket closed by other side")
                await self._reset_connection()
        except OSError as ex:
            # Usually this indicates that the socket was closed.
            _LOGGER.debug("Socket closed: %s.", ex)
            await self._reset_connection()
        except Exception:
            _LOGGER.exception("Unexpected exception in socket handling")
            await self._reset_connection()

    async def _read_one_message(
        self,
    ) -> Optional[tuple[comms.Hdr, comms.Message]]:
        """Helper routine called by `_read()` to read and decode a single message.

        Returns the decoded header and message, or None if an error occurred
        decoding the message.
        """
        # Need to check reader for None to satisfy mypy, but this is already
        # checked in _read() above.
        if not self._reader:
            return None

        header_decoder = self._registry.header_decoder
        checksum_calculator = self._registry.checksum_calculator

        # Ensure variables are bound for logging in the exception handler.
        header_buffer = None
        message_buffer = None
        crc = None

        try:
            header_buffer = await self._reader.readexactly(
                header_decoder.header_length,
            )
            header_result = header_decoder.decode(header_buffer)
            header_result.assert_complete()

            header = header_result.header

            message_buffer = await self._reader.readexactly(header.message_length)
            crc = await self._reader.readexactly(checksum_calculator.checksum_length)

            if _LOGGER.isEnabledFor(logging.DEBUG):
                all_bytes = header_buffer + message_buffer + crc
                _LOGGER.debug("Read Raw     : %s", all_bytes)
                _LOGGER.debug("...  CRC     : %s", crc)
                _LOGGER.debug("...  Header  : %s", header)

            crc_data = header_result.checksum_data + message_buffer
            if not checksum_calculator.validate(crc_data, crc):
                _LOGGER.debug(
                    "CRC validation failed: %s, %s, %s", header, crc_data, crc
                )
                return None

            message_decoder = self._registry.get_decoder(header.message_id)
            message_result = message_decoder.decode(message_buffer, header)
            message_result.assert_complete()
            _LOGGER.debug("...  Message : %s", message_result.message)
        except comms.DecodeError:
            all_bytes = bytearray()
            if header_buffer:
                all_bytes.extend(header_buffer)
            if message_buffer:
                all_bytes.extend(message_buffer)
            if crc:
                all_bytes.extend(crc)
            _LOGGER.exception("Error decoding bytes: %s", all_bytes)

            return None

        return (header, message_result.message)

    async def _write(self, header: comms.Hdr, message: comms.Message) -> None:
        if not self._writer:
            raise NotConnectedError

        encoded_header = self._registry.header_encoder.encode(header)

        message_encoder = self._registry.get_encoder(message.message_id)
        message_bytes = message_encoder.encode(header, message)

        crc_bytes = self._registry.checksum_calculator.calculate(
            encoded_header.checksum_data + message_bytes
        )

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Write Header : %s", header)
            _LOGGER.debug("...   Message: %s", message)
            _LOGGER.debug("...   CRC    : %s", crc_bytes)
            all_bytes = encoded_header.header_bytes + message_bytes + crc_bytes
            _LOGGER.debug("...   Raw    : %s", all_bytes)

        try:
            self._writer.write(encoded_header.header_bytes)
            self._writer.write(message_bytes)
            self._writer.write(crc_bytes)
            await self._writer.drain()
        except OSError as ex:
            # Connection errors may turn up here rather than in the read method.
            # Usually it just means the remote end closed the socket.
            _LOGGER.debug("Socket error %s while sending %s", ex, message)
            await self._reset_connection()

    async def _notify_connection_changed(self, *, connected: bool) -> None:
        await self._notify_subscribers(
            [s(connected=connected) for s in self._connection_subscribers],
        )

    async def _notify_message_received(
        self, header: comms.Hdr, message: comms.Message
    ) -> None:
        await self._notify_subscribers(
            [s(header, message) for s in self._message_subscribers],
        )

    async def _notify_subscribers(self, callbacks: Iterable[Awaitable[Any]]) -> None:
        for coro in asyncio.as_completed(callbacks):
            try:
                _ = await coro
            except Exception:  # noqa: PERF203
                _LOGGER.exception("Exception from subscriber")


T = TypeVar("T")


async def _delay(coro: Awaitable[T], delay: float) -> T:
    """Delays the execution of an awaitable."""
    await asyncio.sleep(delay)
    return await coro
