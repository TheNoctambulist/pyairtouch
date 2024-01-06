"""Definition of the Group Names Message (0x1FFF12).

The Group Names message provides the names of each zone within the AirTouch 4
system. For a mapping of ACs to Groups, refer to the AC Ability Message
(0x1FFF11).

To request the zone names, a Group Names Request must be sent to the AirTouch.
Since the Group Names Request uses the same message ID as the Group Names
Message, a common encoder and decoder are used.

This message is a sub-message of the Extended Message.

The Group Names message is not documented in v1.1 of the AirTouch 4 interface
specification. The contents of this message have been reverse engineered from
other interface implementations.
"""  # noqa: N999

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x1F_ext import ExtendedMessageSubHeader
from pyairtouch.comms import MessageDecodeResult, encoding

MESSAGE_ID = 0xFF12


@dataclass
class GroupNamesMessage(comms.Message):
    """The Group Names Message."""

    group_names: Mapping[int, str]
    """Mapping of group number to group name."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class GroupNamesRequest(comms.Message):
    """Request for Group Names."""

    group_number: int | Literal["ALL"]
    """Request group names for a single group or all groups."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_GROUP_NAME_LENGTH = 8
"""Length of the group name string within the group names message."""
_PER_GROUP_SIZE = 1 + _GROUP_NAME_LENGTH
"""Total size of the per-group data in the Group Names Message.

One byte for the group number, then the group name.
"""


class GroupNamesEncoder(
    comms.MessageEncoder[
        x1F_ext.ExtendedMessageSubHeader, GroupNamesMessage | GroupNamesRequest
    ]
):
    """Encoder for the Group Names Message and Request.

    Handles both the message and the request since they have the same message ID.
    """

    @override
    def size(self, message: GroupNamesMessage | GroupNamesRequest) -> int:
        if isinstance(message, GroupNamesRequest):
            return 0 if message.group_number == "ALL" else 1

        return _PER_GROUP_SIZE * len(message.group_names)

    @override
    def encode(
        self,
        header: ExtendedMessageSubHeader,
        message: GroupNamesMessage | GroupNamesRequest,
    ) -> bytes:
        if isinstance(message, GroupNamesRequest):
            if message.group_number == "ALL":
                return b""  # No content
            return bytes((message.group_number,))

        buffer = bytearray()
        for group_number, group_name in message.group_names.items():
            buffer.append(group_number)
            buffer.extend(encoding.encode_c_string(group_name, _GROUP_NAME_LENGTH))
        return buffer


class GroupNamesDecoder(
    comms.MessageDecoder[
        x1F_ext.ExtendedMessageSubHeader, GroupNamesMessage | GroupNamesRequest
    ]
):
    """Decoder for the Group Names Message and Request.

    Handles both the message and the request since they have the same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: ExtendedMessageSubHeader
    ) -> MessageDecodeResult[GroupNamesMessage | GroupNamesRequest]:
        # If there is no data, this is a request for all groups
        if header.message_length == 0:
            return comms.MessageDecodeResult(
                message=GroupNamesRequest(group_number="ALL"),
                remaining=buffer,
            )

        # If there is only one byte, then this is a request for a single group
        if header.message_length == 1:
            return comms.MessageDecodeResult(
                message=GroupNamesRequest(group_number=buffer[0]),
                remaining=buffer[1:],
            )

        # Otherwise, decode group names for one or more groups:
        if (header.message_length % (1 + _GROUP_NAME_LENGTH)) != 0:
            raise comms.DecodeError(
                f"Message length ({header.message_length}) is not "
                f"a multiple of the group data size ({_PER_GROUP_SIZE})."
            )

        group_names: dict[int, str] = {}
        for _ in range(header.message_length // _PER_GROUP_SIZE):
            group_number = buffer[0]
            group_name = encoding.decode_c_string(buffer[1:_PER_GROUP_SIZE])

            group_names[group_number] = group_name

            buffer = buffer[_PER_GROUP_SIZE:]

        return comms.MessageDecodeResult(
            message=GroupNamesMessage(group_names),
            remaining=buffer,
        )
