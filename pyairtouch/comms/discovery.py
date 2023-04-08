"""AirTouch discovery communication."""

import asyncio
import socket
from collections.abc import Callable, Coroutine, Sequence
from typing import Any, Generic

from typing_extensions import override

import pyairtouch.comms.log
from pyairtouch import comms

_LOGGER = pyairtouch.comms.log.getLogger(__name__)

_DISCOVERY_REQUEST_INTERVAL = 1.0
"""Interval in seconds for sending discovery requests."""
_DISCOVERY_MAX_REQUESTS = 3
"""Maximum amount of discovery requests to send before giving up."""


class AirTouchDiscoverer(Generic[comms.DiscoveryRequest_co, comms.TDiscoveryResponse]):
    """Discovers AirTouch consoles on the network.

    Performs discovery in accordance with a specific discovery configuration.
    """

    def __init__(  # noqa: D107
        self,
        discovery_config: comms.DiscoveryConfig[
            comms.DiscoveryRequest_co, comms.TDiscoveryResponse
        ],
    ) -> None:
        self._discovery_config = discovery_config

    async def search(self) -> Sequence[comms.TDiscoveryResponse]:
        """Initiate a search for AirTouch consoles on the network.

        There is no need to use a timeout for the search. It will terminate
        after a reasonable period if no AirTouch consoles are discovered.
        """
        # Use a set to filter out any duplicates that might slip through
        responses: set[comms.TDiscoveryResponse] = set()

        transport = await self._open_socket(responses)

        request = self._discovery_config.request_factory()
        remote_address = ("255.255.255.255", self._discovery_config.remote_port)

        count = 0
        while not responses and count < _DISCOVERY_MAX_REQUESTS:
            count += 1
            _LOGGER.debug(
                "Sending discovery request (%d): %s",
                count,
                request.data,
            )
            transport.sendto(request.data, remote_address)
            # We always wait for the full interval instead of exiting after the
            # first response to allow time for multiple AirTouch consoles to reply.
            await asyncio.sleep(_DISCOVERY_REQUEST_INTERVAL)

        transport.close()

        return list(responses)

    async def _open_socket(
        self, responses: set[comms.TDiscoveryResponse]
    ) -> asyncio.DatagramTransport:
        """Open a socket for sending/receiving broadcast discovery messages.

        Args:
            responses: a list in which to store responses.
        """
        sock = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP
        )
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        local_address = ("0.0.0.0", self._discovery_config.local_port)  # noqa: S104 (binding to all interfaces is intentional)
        sock.bind(local_address)

        async def on_discovery_reponse(response: comms.TDiscoveryResponse) -> None:
            responses.add(response)

        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            protocol_factory=lambda: _DiscoveryDecodeProtocol(
                loop=loop,
                response_type=self._discovery_config.response_type,
                decoder=self._discovery_config.decoder,
                callback=on_discovery_reponse,
            ),
            sock=sock,
        )

        return transport


_ResponseCallback = Callable[[comms.TDiscoveryResponse], Coroutine[Any, Any, None]]


class _DiscoveryDecodeProtocol(
    asyncio.DatagramProtocol,
    Generic[comms.DiscoveryRequest_co, comms.TDiscoveryResponse],
):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        decoder: comms.DiscoveryDecoder[
            comms.DiscoveryRequest_co, comms.TDiscoveryResponse
        ],
        response_type: type[comms.TDiscoveryResponse],
        callback: _ResponseCallback[comms.TDiscoveryResponse],
    ) -> None:
        self._loop = loop
        self._decoder = decoder
        self._response_type = response_type
        self._callback = callback

        self._background_tasks: set[asyncio.Task[Any]] = set()

    @override
    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        _LOGGER.debug("Received datagram: %s", data)

        if not self._decoder.match(data):
            _LOGGER.debug("... Message      : <unknown>")
            return

        try:
            message = self._decoder.decode(data)
            _LOGGER.debug("... Message      : %s", message)

            if isinstance(message, self._response_type):
                task = self._loop.create_task(self._callback(message))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        except comms.DecodeError:
            _LOGGER.exception("Error decoding discovery response")
