"""Definition of the AC Error Information Message (0x1FFF10).

AC Error Information messages contain detailed error descriptions for the ACs in
the AirTouch 4 system.

To request the AC Error Information an AC Error Information Request must be sent
to the AirTouch 4. Since the AC Error Information Request uses the same ID as
the AC Error Information Message, a shared encoder and decoder are used.

This message is a sub-message of the Extended Message.
"""  # noqa: N999

from dataclasses import dataclass
from typing import Optional

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x1F_ext import ExtendedMessageSubHeader
from pyairtouch.comms import MessageDecodeResult, encoding

MESSAGE_ID = 0xFF10


@dataclass
class AcErrorInformationMessage(comms.Message):
    """The AC Error Information Message."""

    ac_number: int
    """The AC to which the error applies."""
    error_info: Optional[str]
    """The error information, or None if there is no error for this AC."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class AcErrorInformationRequest(comms.Message):
    """Request for AC Error Information."""

    ac_number: int
    """The AC for which error information should be retrieved."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


class AcErrorInformationEncoder(
    comms.MessageEncoder[
        x1F_ext.ExtendedMessageSubHeader,
        AcErrorInformationMessage | AcErrorInformationRequest,
    ]
):
    """Encoder for AC Error Information Message and Request.

    Handles both the message and request since they share a common message ID.
    """

    @override
    def size(
        self, message: AcErrorInformationMessage | AcErrorInformationRequest
    ) -> int:
        if isinstance(message, AcErrorInformationRequest):
            return 1  # AC number only
        # Will result in the string being encoded twice, but we don't expect to
        # encode this message very often, so there's no need to optimise this.
        if message.error_info:
            return 2 + len(message.error_info.encode(encoding=encoding.STRING_ENCODING))
        return 2

    @override
    def encode(
        self,
        _: ExtendedMessageSubHeader,
        message: AcErrorInformationMessage | AcErrorInformationRequest,
    ) -> bytes:
        buffer = bytearray()
        buffer.append(message.ac_number & 0xFF)

        if isinstance(message, AcErrorInformationMessage):
            if message.error_info:
                error_string = message.error_info.encode(
                    encoding=encoding.STRING_ENCODING
                )
                buffer.append(len(error_string))
                buffer.extend(error_string)
            else:
                buffer.append(0)

        return buffer


class AcErrorInformationDecoder(
    comms.MessageDecoder[
        x1F_ext.ExtendedMessageSubHeader,
        AcErrorInformationMessage | AcErrorInformationRequest,
    ]
):
    """Decoder for the AC Error Information and Request.

    Handles both the message and the request since they share the same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: ExtendedMessageSubHeader
    ) -> MessageDecodeResult[AcErrorInformationMessage | AcErrorInformationRequest]:
        ac_number = buffer[0]
        # If the data only contains the AC number then this is a request
        if header.message_length == 1:
            return comms.MessageDecodeResult(
                message=AcErrorInformationRequest(ac_number), remaining=buffer[1:]
            )

        # Otherwise this is the error information
        error_length = buffer[1]
        error_start = 2
        error_end = error_start + error_length

        error = None
        if error_length > 0:
            error = buffer[error_start:error_end].decode(
                encoding=encoding.STRING_ENCODING
            )

        return comms.MessageDecodeResult(
            message=AcErrorInformationMessage(
                ac_number=ac_number,
                error_info=error,
            ),
            remaining=buffer[error_end:],
        )
