"""Provides UDP broadcast communication support."""

import asyncio
import socket

Address = tuple[str, int]


class _DatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, datagram_buffer_size: int = 0) -> None:
        """Initialise the DatagramProtocol.

        Args:
            datagram_buffer_size: optional upper bound for the datagram buffer.
                If 0 then the queue will be unbounded.
        """
        super().__init__()
        self._buffer: asyncio.Queue[tuple[bytes, Address]] = asyncio.Queue(
            maxsize=datagram_buffer_size
        )

    def datagram_received(self, data: bytes, addr: Address) -> None:
        self._buffer.put_nowait((data, addr))

    async def recvfrom(self) -> tuple[bytes, Address]:
        return await self._buffer.get()


class DatagramSocket:
    """A socket for UDP communication via asyncio."""

    def __init__(
        self, transport: asyncio.DatagramTransport, protocol: _DatagramProtocol
    ) -> None:
        """Initialise the DatagramSocket."""
        self._transport = transport
        self._protocol = protocol

    def sendto(self, data: bytes | bytearray, addr: Address) -> None:
        """Send a datagram over the socket."""
        self._transport.sendto(data, addr)

    async def recvfrom(self) -> tuple[bytes, Address]:
        """Read a datagram from socket."""
        return await self._protocol.recvfrom()

    def close(self) -> None:
        """Close the socket."""
        self._transport.close()


async def create_udp_broadcast_socket(
    local_addr: tuple[str, int] | None,
) -> DatagramSocket:
    """Create a DatagramSocket for UDP broadcast."""
    loop = asyncio.get_running_loop()
    sock = socket.socket(
        family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP
    )
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if local_addr:
        sock.bind(local_addr)
    transport, protocol = await loop.create_datagram_endpoint(
        protocol_factory=_DatagramProtocol,
        sock=sock,
    )
    return DatagramSocket(transport, protocol)
