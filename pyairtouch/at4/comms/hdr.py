"""Definitions of the AirTouch 4 messages's header.

The message header contains the message ID and address information as required
by the communication protocol.
"""

import struct
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.comms import HeaderDecodeResult, HeaderEncodeResult

ADDRESS_AIRTOUCH = 0x80
ADDRESS_AIRTOUCH_EXTENDED = 0x90
ADDRESS_CLIENT = 0xB0
"""Known addresses for communication with the AirTouch 4.

The AirTouch console address is different depending on whether a normal message
or an extended message (0x1F) is being sent/received. The address of the client
is always the same.

The AirTouch may send messages addressed to other clients. These are supposed to
be ignored, but can be decoded if the message type is known.
"""

CRC_LENGTH = 2
"""The length of the checksum for an AirTouch 4 message.

AirTouch 4 uses CRC16 MODBUS, so two bytes are required.
"""


@dataclass
class At4Header:
    """The AirTouch 4 header.

    Refer to the ADDRESS_* constants for typical address values.

    packet_id is an arbitrary identifier for each packet and can just be a
    sequentially incrementing number.
    """

    to_address: int
    from_address: int
    packet_id: int
    message_id: int
    message_length: int
    """Length in bytes of the contained message (excluding the header)."""


_STRUCT = struct.Struct("!2sBBBBH")

_PREFIX = b"\x55\x55"

# The checksum excludes the header prefix.
_CHECKSUM_DATA_START = len(_PREFIX)


class HeaderEncoder(comms.HeaderEncoder[At4Header]):
    """Encoder for the AirTouch 4 header."""

    @override
    def encode(self, header: At4Header) -> HeaderEncodeResult:
        header_bytes = _STRUCT.pack(
            _PREFIX,
            header.to_address,
            header.from_address,
            header.packet_id,
            header.message_id,
            header.message_length,
        )
        return comms.HeaderEncodeResult(
            header_bytes=header_bytes, checksum_data=header_bytes[_CHECKSUM_DATA_START:]
        )


class HeaderDecoder(comms.HeaderDecoder[At4Header]):
    """Decoder for the AirTouch 4 header."""

    @override
    @property
    def header_length(self) -> int:
        return _STRUCT.size

    @override
    def decode(self, buffer: bytes | bytearray) -> HeaderDecodeResult[At4Header]:
        (
            prefix,
            to_address,
            from_address,
            packet_id,
            message_id,
            message_length,
        ) = _STRUCT.unpack_from(buffer)

        if prefix != _PREFIX:
            raise comms.DecodeError(f"Unknown header prefix: {prefix}")

        return comms.HeaderDecodeResult(
            header=At4Header(
                to_address=to_address,
                from_address=from_address,
                packet_id=packet_id,
                message_id=message_id,
                message_length=message_length,
            ),
            remaining=buffer[_STRUCT.size :],
            checksum_data=buffer[_CHECKSUM_DATA_START : _STRUCT.size],
        )
