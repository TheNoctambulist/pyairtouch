"""Definition of the Console Version Message (0x1FFF30).

Console Version messages provide the version number of AirTouch 5 system and an
indication of whether an update is available.

To request the Console Version a Console Version Request must be sent to the AirTouch 5.
Since the Console Version Request uses the same ID as the Console Version Message, a
shared Encoder and Decoder are used.

This message is a sub-message of the Extended Message.
"""  # noqa: N999

from collections.abc import Sequence
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import x1F_ext
from pyairtouch.comms import encoding

MESSAGE_ID = 0xFF30


@dataclass
class ConsoleVersionMessage(comms.Message):
    """The Console Version Message."""

    update_available: bool
    versions: Sequence[str]
    """The versions of all AirTouch consoles.

    Up to two consoles according to the communication protocol. The first
    version is the version of the console that we are communicating with.
    """

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class ConsoleVersionRequest(comms.Message):
    """Request for console version information."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


class ConsoleVersionEncoder(
    comms.MessageEncoder[
        x1F_ext.ExtendedMessageSubHeader, ConsoleVersionMessage | ConsoleVersionRequest
    ]
):
    """Encoder for the Console Version Message and Request.

    Handles both the message and the request because they share the same message ID.
    """

    @override
    def size(self, message: ConsoleVersionMessage | ConsoleVersionRequest) -> int:
        if isinstance(message, ConsoleVersionRequest):
            return 0
        # Length calculation requires the string to be encoded twice, but we
        # don't expect to encode this message very often.
        return 2 + len(
            ",".join(message.versions).encode(encoding=encoding.STRING_ENCODING)
        )

    @override
    def encode(
        self,
        _: x1F_ext.ExtendedMessageSubHeader,
        message: ConsoleVersionMessage | ConsoleVersionRequest,
    ) -> bytes:
        if isinstance(message, ConsoleVersionRequest):
            return b""  # No content for a console version request

        buffer = bytearray()
        buffer.append(1 if message.update_available else 0)
        encoded_versions = ",".join(message.versions).encode(
            encoding=encoding.STRING_ENCODING
        )
        buffer.append(len(encoded_versions))
        buffer.extend(encoded_versions)
        return buffer


class ConsoleVersionDecoder(
    comms.MessageDecoder[
        x1F_ext.ExtendedMessageSubHeader, ConsoleVersionMessage | ConsoleVersionRequest
    ]
):
    """Decoder for the Console Version Message and Request.

    Handles both the message and the request because they have the same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: x1F_ext.ExtendedMessageSubHeader
    ) -> comms.MessageDecodeResult[ConsoleVersionMessage | ConsoleVersionRequest]:
        # If there is no data then this is a version request
        if header.message_length == 0:
            return comms.MessageDecodeResult(
                message=ConsoleVersionRequest(),
                remaining=buffer,
            )

        # Otherwise this is a console version message
        update_raw = buffer[0]
        version_length = buffer[1]
        version_start = 2
        version_end = version_start + version_length
        versions = buffer[version_start:version_end].decode(
            encoding=encoding.STRING_ENCODING
        )

        return comms.MessageDecodeResult(
            message=ConsoleVersionMessage(
                update_available=(update_raw != 0), versions=versions.split(",")
            ),
            remaining=buffer[version_end:],
        )
