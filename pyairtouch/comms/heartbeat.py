"""Utilities to support heartbeat messages for AirTouch interfaces.

A heartbeat implementation is required to reliably detect and recover from
half-open TCP connections. A half-open connection can only be detected by
writing data to the socket. In a stable environment when the air-conditioner is
not running the AirTouch may not send any messages for a long time so it is not
feasible to just use a timeout for received messages.

No explicit heartbeat is defined in the interface specification for AirTouch 4
and AirTouch 5, however it's possible to send one of the request messages and
check for a corresponding response message.
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic

import pyairtouch.comms.socket
from pyairtouch import comms

_LOGGER = logging.getLogger(__name__)

DEFAULT_HEARTBEAT_INTERVAL = 300.0
"""Default heartbeat interval in seconds."""

DEFAULT_HEARTBEAT_RESPONSE_DELAY = 30.0
"""Default delay before a heartbeat response is considered to have timed out."""


@dataclass
class HeartbeatConfig:
    """Configuration for the Heartbeat Manager."""

    message: comms.Message
    """A message to be sent periodically as a heartbeat."""
    response_match: Callable[[comms.Message], bool]
    """A match function to identifer responses to a heartbeat."""
    interval: float = DEFAULT_HEARTBEAT_INTERVAL
    """The interval in seconds at which to send heartbeat messages."""
    timeout: float = DEFAULT_HEARTBEAT_INTERVAL + DEFAULT_HEARTBEAT_RESPONSE_DELAY
    """The maximum duration in seconds to wait between heartbeat responses.

    After this timeout, the connection will be reset before considering the
    connection down.
    """


class HeartbeatManager(Generic[comms.Hdr]):
    """Periodically sends a heartbeat message and checks for responses.

    Sends the provided heartbeat message periodically and checks for a response.
    If no response is received within the timeout interval, the socket
    connection is reset.

    The timeout interval for a heartbeat message is 1.5 times the heartbeat interval.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        socket: pyairtouch.comms.socket.AirTouchSocket[comms.Hdr],
        config: HeartbeatConfig,
    ) -> None:
        """Initialise the HeartbeatManager.

        Args:
            loop: The event loop used for scheduling background tasks.
            socket: The socket for sending heartbeat messages.
            config: Configuration for the heartbeat manager.
        """
        self._loop = loop
        self._socket = socket
        self._config = config

        self._heartbeat_tasks: list[asyncio.Task[None]] = []
        self._response_received = asyncio.Event()

    async def start(self) -> None:
        """Start sending heartbeat messages and monitoring the connection."""
        if self._heartbeat_tasks:
            # Already started.
            return

        self._response_received.clear()
        self._socket.subscribe_on_message_received(self._message_received)
        self._heartbeat_tasks.append(self._loop.create_task(self._heartbeat_loop()))
        self._heartbeat_tasks.append(
            self._loop.create_task(self._heartbeat_timeout_loop())
        )

    async def stop(self) -> None:
        """Stop sending heartbeat messages."""
        if not self._heartbeat_tasks:
            # Not started
            return

        for t in self._heartbeat_tasks:
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await t
        self._heartbeat_tasks.clear()

        self._socket.unsubcribe_on_message_received(self._message_received)

    async def _message_received(self, _: comms.Hdr, message: comms.Message) -> None:
        if self._config.response_match(message):
            # We count any heartbeat response even if it wasn't necessarily
            # triggered by a heartbeat message since it still indicates that the
            # connection is up.
            self._response_received.set()

    async def _heartbeat_loop(self) -> None:
        """The heartbeat loop implementation.

        Sends a heartbeat message at the specified interval and checks that a
        response has been received within two interval cycles. If no response
        has been received the socket is reset by disconnecting and re-connecting.

        The heartbeat message is only sent if the socket is connected.
        """
        # Run until cancelled.
        while True:
            # Using asyncio.gather minimises drift by running the sleep
            # concurrently with the sending of the message.
            await asyncio.gather(
                asyncio.sleep(self._config.interval),
                self._send_heartbeat_message(),
            )

    async def _send_heartbeat_message(self) -> None:
        if self._socket.is_connected:
            _LOGGER.debug("Sending heartbeat message")

            await self._socket.send(
                message=self._config.message,
                retry_policy=pyairtouch.comms.socket.RETRY_CONNECTED,
            )

    async def _heartbeat_timeout_loop(self) -> None:
        """The heartbeat timeout loop implementation.

        Waits until the next timeout period, and if no heartbeat response has
        been received resets the socket connection.
        """
        # Run until cancelled.
        while True:
            try:
                async with asyncio.timeout(None) as timeout:
                    while True:
                        await self._response_received.wait()
                        timeout.reschedule(self._loop.time() + self._config.timeout)
                        self._response_received.clear()
            except TimeoutError:
                if self._socket.is_connected:
                    _LOGGER.debug("Heartbeat timed out, resetting connection")
                    await self._socket.reset_connection()
