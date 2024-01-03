"""Definition of the Zone Names Message (0x1FFF13).

Zone Name messages provide the name of each zone in the AirTouch 5 system. For a
mapping of ACs to Zones, refer to the AC Ability Message (0x1FFF11).

To request the Zone Names a Zone Names Request must be sent to the AirTouch 5.
Since the Zone Names Request uses the same ID as the Zone Names Message, a
shared Encoder and Decoder are used.

This message is a sub-message of the Extended Message.
"""  # noqa: N999

import dataclasses
from collections.abc import Mapping
from functools import reduce
from typing import Literal

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import x1F_ext
from pyairtouch.comms import encoding

MESSAGE_ID = 0xFF13


@dataclasses.dataclass
class ZoneNamesMessage(comms.Message):
    """The Zone Names Message."""

    zone_names: Mapping[int, str]
    """Mapping of zone number to zone name."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclasses.dataclass
class ZoneNamesRequest(comms.Message):
    """Request for Zone Names."""

    zone_number: int | Literal["ALL"]
    """Request Zone Names for a single zone or all zones."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


class ZoneNamesEncoder(
    comms.MessageEncoder[
        x1F_ext.ExtendedMessageSubHeader, ZoneNamesMessage | ZoneNamesRequest
    ]
):
    """Encoder for the Zone Names Message and Request.

    Handles both the message and the request because they have the same message ID.
    """

    @override
    def size(self, msg: ZoneNamesMessage | ZoneNamesRequest) -> int:
        if isinstance(msg, ZoneNamesRequest):
            return 0 if msg.zone_number == "ALL" else 1

        length_fields_size = len(msg.zone_names)  # One byte per zone name
        # Length calculation requires the string to be encoded twice, but we
        # don't expect to encode this message very often.
        return reduce(
            lambda total, name: total
            + len(name.encode(encoding=encoding.STRING_ENCODING)),
            msg.zone_names.values(),
            length_fields_size,
        )

    @override
    def encode(
        self,
        hdr: x1F_ext.ExtendedMessageSubHeader,
        msg: ZoneNamesMessage | ZoneNamesRequest,
    ) -> bytes:
        if isinstance(msg, ZoneNamesRequest):
            if msg.zone_number == "ALL":
                return b""  # No content
            return bytes([msg.zone_number])

        buffer = bytearray()
        for zone_number, zone_name in msg.zone_names.items():
            buffer.append(zone_number)
            encoded_name = zone_name.encode(encoding=encoding.STRING_ENCODING)
            buffer.append(len(encoded_name))
            buffer.extend(encoded_name)
        return buffer


class ZoneNamesDecoder(
    comms.MessageDecoder[
        x1F_ext.ExtendedMessageSubHeader, ZoneNamesMessage | ZoneNamesRequest
    ]
):
    """Decoder for the Zone Names Message and Request.

    Handles both the messaage and the request because they have the same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, hdr: x1F_ext.ExtendedMessageSubHeader
    ) -> comms.MessageDecodeResult[ZoneNamesMessage | ZoneNamesRequest]:
        # If there is no data, this is a request for all zones
        if hdr.message_length == 0:
            return comms.MessageDecodeResult(
                message=ZoneNamesRequest(zone_number="ALL"),
                remaining=buffer,
            )

        # If there is only one byte, then this is a request for a specific zone
        if hdr.message_length == 1:
            return comms.MessageDecodeResult(
                message=ZoneNamesRequest(zone_number=buffer[0]),
                remaining=buffer[1:],
            )

        # Otherwise, decode zone names for one or more zones:
        offset = 0
        zone_names: dict[int, str] = {}
        while offset < hdr.message_length:
            zone_number = buffer[offset]
            name_length = buffer[offset + 1]
            name_start = offset + 2
            name_end = name_start + name_length

            if name_end > hdr.message_length:
                raise comms.DecodeError("Zone name exceeds message length")

            zone_name = buffer[name_start:name_end].decode(
                encoding=encoding.STRING_ENCODING
            )

            zone_names[zone_number] = zone_name

            offset = name_end

        if offset != hdr.message_length:
            raise comms.DecodeError(
                f"Zone names didn't consume entire message buffer. "
                f"{hdr.message_length - offset} bytes remaining"
            )

        return comms.MessageDecodeResult(
            message=ZoneNamesMessage(zone_names=zone_names),
            remaining=buffer[offset:],
        )
