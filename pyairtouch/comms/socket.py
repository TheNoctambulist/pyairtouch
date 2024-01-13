"""TCP socket abstraction for sending and receiving messages.

Provides a high-level API over a TCP socket to send and receive messages as
objects.
"""

import asyncio
import contextlib
import logging
from collections import deque
from collections.abc import Awaitable, Callable, Coroutine, Iterable
from dataclasses import dataclass
from typing import Any, Generic, Optional, Protocol, TypeVar

import pyairtouch.comms.log
from pyairtouch import comms

_LOGGER = pyairtouch.comms.log.getLogger(__name__)

_CONNECT_RETRY_DELAY = 2.0
"""Delay after which a connection attempt will be retried."""


class NotOpenError(RuntimeError):
    """Raised when an attempt is made to use a socket that is not open."""


class QueueOverflowError(RuntimeError):
    """Raised when the socket message queue overflows."""


class ConnectionSubscriber(Protocol):
    """Protocol for connection change subscribers."""

    def __call__(self, *, connected: bool) -> Awaitable[None]:
        """Connection state has changed.

        Args:
            connected: whether or not the socket is connected.
        """


MessageSubscriber = Callable[[comms.Hdr, comms.Message], Awaitable[None]]


@dataclass(frozen=True)
class _MessageQueueEntry(Generic[comms.Hdr]):
    """An entry in the message queue."""

    header: comms.Hdr
    """The header for the message."""
    message: comms.Message
    """The message to be sent."""

    retries_remaining: int
    """Number of remaining times this message should be retried.

    If re-sending the message fails, the message will be re-added to the retry
    queue up to retries_remaining times.
    """
    expiry: float
    """Message expiry time according to the event loop's clock.

    The message will not be sent or retried if the expiry has passed.
    """


@dataclass
class RetryPolicy:
    """Policy for retrying message sending."""

    max_retries: int
    """The maximum number of times this message can be retried if sending fails."""

    max_lifetime: float
    """The maximum lifetime of this message in seconds.

    After this lifetime expires, an unsent message will be dropped from the
    message buffer.
    """


DEFAULT_MESSAGE_LIFETIME = 30.0
"""Default message retry lifetime in seconds."""

RETRY_IDEMPOTENT = RetryPolicy(
    max_retries=2,
    max_lifetime=DEFAULT_MESSAGE_LIFETIME,
)
"""Typical retry policy for idempotent messages.

Idempotent messages can be sent multiple times without any cumulative effect.
For example, a request to turn the AC on would have no effect if the AC is
already turned on. A higher retry count and lifetime is appropriate for these
messages because there are no consequences if we retry an already sent message.
"""

RETRY_NON_IDEMPOTENT = RetryPolicy(
    max_retries=0,
    max_lifetime=DEFAULT_MESSAGE_LIFETIME,
)
"""Typical retry policy for non-idempotent messages.

Non-idempotent messages could have unexpected effects if they are sent twice.
Since it is not possible to guarantee that a message has not been sent under
error conditions, retries are not permitted at all for non-idempotent messages.
"""

RETRY_CONNECTED = RetryPolicy(
    max_retries=0,
    max_lifetime=1.0,
)
"""Typical retry policy for messages only sent while connected.

This retry policy is used for messages that should be dropped if the
socket is not connected within a very short interval of being sent. Effectively
messages that are dropped immediately if the socket is not connected.
"""

MAX_MESSAGE_QUEUE_SIZE = 10
"""Maximum number of pending unsent messages."""


class AirTouchSocket(Generic[comms.Hdr]):
    """A socket for communicating with an AirTouch system.

    The socket must be opened before `send()` can be called. Sending a message
    when the socket is open but not connected will not result in an error.
    Messages will be buffered for a short period of time and then sent when a
    connection is established. If the connection is not established within the
    requested expiry time of the message it will be dropped.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        host: str,
        port: int,
        registry: comms.MessageRegistry[comms.Hdr],
    ) -> None:
        """Initialise the AirTouch socket.

        Args:
            loop: The event loop for scheduling tasks.
            host: Host name or IP address for the AirTouch.
            port: Remote port number for the TCP connection.
            registry: Registry for message encoders and decoders.
        """
        self._loop = loop
        self.host = host
        self.port = port
        self._registry = registry

        self.is_open = False
        self.is_connected = False

        self._background_tasks: set[asyncio.Task[Any]] = set()

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

        self._message_queue: deque[_MessageQueueEntry[comms.Hdr]] = deque()

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

    async def send(self, message: comms.Message, retry_policy: RetryPolicy) -> None:
        """Send a message to the AirTouch.

        If the socket is open, but not connected messages will be buffered and,
        subject to the specified retry policy, sent at a time when the socket is
        successfully connected.

        Raises:
            NotOpenError if the socket is not open.
            QueueOverflowError if the message queue capacity is exceeded and the
                message cannot be queued for sending.
        """
        message_encoder = self._registry.get_encoder(message.message_id)
        message_length = message_encoder.size(message)
        header = self._registry.header_factory.create_from_message(
            message, message_length
        )
        await self.send_with_header(header, message, retry_policy)

    async def send_with_header(
        self,
        header: comms.Hdr,
        message: comms.Message,
        retry_policy: RetryPolicy,
    ) -> None:
        """Send a message with a custom header to the AirTouch.

        If the socket is open, but not connected messages will be buffered and,
        subject to the specified retry policy, sent at a time when the socket is
        successfully connected.

        Raises:
            NotOpenError if the socket is not open.
            QueueOverflowError if the message queue capacity is exceeded and the
                message cannot be queued for sending.
        """
        if not self.is_open:
            raise NotOpenError

        self._enqueue_message(
            _MessageQueueEntry(
                header=header,
                message=message,
                retries_remaining=retry_policy.max_retries,
                expiry=self._loop.time() + retry_policy.max_lifetime,
            )
        )
        await self._drain_message_queue()

    def _enqueue_message(self, entry: _MessageQueueEntry[comms.Hdr]) -> None:
        """Add a message to the queue.

        Discards any expired messages.

        Raises:
            QueueOverflowError if the message queue capacity is exceeded and the
                message cannot be queued for sending.
        """
        # Drop expired messages
        now = self._loop.time()
        for i in reversed(range(len(self._message_queue))):
            entry = self._message_queue[i]
            if now >= entry.expiry:
                del self._message_queue[i]
                self._log_dropped_message(entry, "expired")

        if len(self._message_queue) >= MAX_MESSAGE_QUEUE_SIZE:
            raise QueueOverflowError

        self._message_queue.append(entry)

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

        task = self._loop.create_task(coro)
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

            # Send any buffered messages
            await self._drain_message_queue()

            self._schedule(self._read())
        except OSError as ex:
            _LOGGER.debug("Unable to connect. Will try again later. Reason: %s", ex)

        if not self.is_connected:
            # Connection failed, so retry after a small delay
            self._schedule(self._connect(), delay=_CONNECT_RETRY_DELAY)

    async def _disconnect(self) -> None:
        _LOGGER.debug("_disconnect: is_connected=%s", self.is_connected)

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

    async def reset_connection(self) -> None:
        """Resets the connection to the AirTouch.

        The connection is reset by disconnecting and re-connecting the
        underlying socket.
        """
        await self._disconnect()
        self._schedule(self._connect())

    async def _read(self) -> None:
        """The main read loop for the AirTouch socket."""
        try:
            while self._reader:
                read_result = await self._read_one_message()
                if read_result:
                    header, message = read_result
                    await self._notify_message_received(header, message)
                else:
                    await self.reset_connection()

        except asyncio.IncompleteReadError:
            _LOGGER.debug("Socket closed")
            if self._writer and not self._writer.is_closing():
                _LOGGER.debug("_read(): Socket closed by other side")
                await self.reset_connection()
        except OSError as ex:
            # Usually this indicates that the socket was closed.
            _LOGGER.debug("_read(): Socket error: %s.", ex)
            await self.reset_connection()
        except Exception:
            _LOGGER.exception("_read(): Unexpected exception in socket handling")
            await self.reset_connection()

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

    async def _drain_message_queue(self) -> None:
        if not self.is_connected:
            # Wait until we're connected
            return

        try:
            while self._message_queue:
                entry = self._message_queue.popleft()

                if self._loop.time() < entry.expiry:
                    await self._write(entry.header, entry.message)
                else:
                    self._log_dropped_message(entry, "expired")

        except (ValueError, NotImplementedError):
            # This indicates an error encoding this message.
            # We shouldn't retry this message, but the connection doesn't need
            # to be reset.
            _LOGGER.exception("Encoding error for message %s", entry.message)

        except OSError as ex:
            # Connection errors may turn up here rather than in the read method.
            # This would often indicate we had a half-open socket where the
            # connection was just killed.
            _LOGGER.debug("write: Socket error %s while sending %s", ex, entry.message)
            if entry.retries_remaining == 0:
                self._log_dropped_message(entry, "max-retries")
            else:
                # Return this message to the head of the queue for a retry
                self._message_queue.appendleft(
                    _MessageQueueEntry(
                        header=entry.header,
                        message=entry.message,
                        retries_remaining=entry.retries_remaining - 1,
                        expiry=entry.expiry,
                    )
                )
            await self.reset_connection()

    async def _write(self, header: comms.Hdr, message: comms.Message) -> None:
        """Writes a single message to the stream.

        Raises:
            OsError for any socket errors identified when writing.
        """
        # This pre-condition will always be satisfied, but checking here keeps
        # mypy happy.
        if not self._writer:
            raise ValueError("_write called when not connected.")

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

        self._writer.write(encoded_header.header_bytes)
        self._writer.write(message_bytes)
        self._writer.write(crc_bytes)
        await self._writer.drain()

    def _log_dropped_message(
        self, message_entry: _MessageQueueEntry[comms.Hdr], reason: str
    ) -> None:
        """Helper method to log when a message has been dropped."""
        _LOGGER.warning(
            "Dropped message (%s):\n    %s\n    %s",
            reason,
            message_entry.header,
            message_entry.message,
        )

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
            except Exception:
                _LOGGER.exception("Exception from subscriber")


T = TypeVar("T")


async def _delay(coro: Awaitable[T], delay: float) -> T:
    """Delays the execution of an awaitable."""
    await asyncio.sleep(delay)
    return await coro
