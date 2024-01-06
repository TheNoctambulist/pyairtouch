"""Definitions of AirTouch 5 message's header.

The message header contains the message ID and address information as required
by the communication protocol.
"""

import struct
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms

ADDRESS_AIRTOUCH = 0x80
ADDRESS_AIRTOUCH_EXTENDED = 0x90
ADDRESS_CLIENT = 0xB0
"""Known addresses for communication with the AirTouch 5.

The AirTouch console address is different depending on whether a command/status
message (0xC0) or an extended message (0x1F) is being sent/received. The address
of the client application is always the same.

The AirTouch will send messages addressed to other clients. These are supposed
to be ignored, but can be decoded if the message type is known.
"""

CRC_LENGTH = 2
"""The length of the checksum for an AirTouch 5 message.

AirTouch 5 uses CRC16 MODBUS, so two bytes are required.
"""


@dataclass
class At5Header:
    """The AirTouch 5 header.

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


# The AirTouch 5 uses two headers for each message:
#  1. a general outer header; and
#  2. a message header.
#
# The outer header is not documented in the communication protocol and does not
# contain any message ID information. The contents of this header have been
# reverse engineered.
#
# To simplify encoding and decoding the two headers are combined into a single struct.
_STRUCT = struct.Struct("!4s2xHH4sBBBBH")

_OUTER_HEADER_PREFIX = b"\x55\x55\x55\xab"
_INNER_HEADER_PREFIX = b"\x55\x55\x55\xaa"

_INTERNAL_HEADER_LENGTH = 10
"""
Number of bytes within the header that are part of the documented internal header.
"""
# The checksum calculation is only calculated over the internal data and
# excludes the header prefix.
_CHECKSUM_DATA_START = (
    _STRUCT.size - _INTERNAL_HEADER_LENGTH + len(_INNER_HEADER_PREFIX)
)


class HeaderEncoder(comms.HeaderEncoder[At5Header]):
    """Encoder for the AirTouch 5 header."""

    @override
    def encode(self, header: At5Header) -> comms.HeaderEncodeResult:
        # Data length in the outer header is calculated as follows:
        # length of the internal header + the message length + the CRC length.
        data_length = _INTERNAL_HEADER_LENGTH + header.message_length + CRC_LENGTH

        header_bytes = _STRUCT.pack(
            _OUTER_HEADER_PREFIX,
            data_length,
            data_length,  # Data Length is repeated
            _INNER_HEADER_PREFIX,
            header.to_address,
            header.from_address,
            header.packet_id,
            header.message_id,
            header.message_length,
        )

        return comms.HeaderEncodeResult(
            header_bytes=header_bytes, checksum_data=header_bytes[_CHECKSUM_DATA_START:]
        )


class HeaderDecoder(comms.HeaderDecoder[At5Header]):
    """Decoder for the AirTouch 5 header."""

    @override
    @property
    def header_length(self) -> int:
        return _STRUCT.size

    @override
    def decode(self, buffer: bytes | bytearray) -> comms.HeaderDecodeResult[At5Header]:
        (
            outer_prefix,
            data_length_1,
            data_length_2,
            inner_prefix,
            to_address,
            from_address,
            packet_id,
            message_id,
            message_length,
        ) = _STRUCT.unpack_from(buffer)

        if outer_prefix != _OUTER_HEADER_PREFIX:
            raise comms.DecodeError(f"Uknown header prefix: {outer_prefix}")

        if data_length_1 != data_length_2:
            raise comms.DecodeError(
                f"data_length_1 ({data_length_1}) != data_length_2 ({data_length_2})"
            )
        if inner_prefix != _INNER_HEADER_PREFIX:
            raise comms.DecodeError(f"Unknown header prefix: {inner_prefix}")

        calculated_data_length = _INTERNAL_HEADER_LENGTH + message_length + CRC_LENGTH
        if data_length_1 != calculated_data_length:
            # It's possible that this would imply some redundant bytes are
            # included in the message data as described in the communication
            # protocol. However (without having performed any analysis of
            # possible message content) we assume that no redundant bytes are
            # ever actually used and just treat this as an error condition.
            raise comms.DecodeError(
                "Inconsistent data lengths in headers: "
                f"{data_length_1} != {calculated_data_length}"
            )

        return comms.HeaderDecodeResult(
            header=At5Header(
                to_address=to_address,
                from_address=from_address,
                packet_id=packet_id,
                message_id=message_id,
                message_length=message_length,
            ),
            remaining=buffer[_STRUCT.size :],
            checksum_data=buffer[_CHECKSUM_DATA_START : _STRUCT.size],
        )
