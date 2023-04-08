"""Definition of the AC Error Information Message (0x1FFF10).

AC Error Information messages contain detailed error descriptions for the ACs in
the AirTouch 5 system.

To request the AC Error Information an AC Error Information Request must be sent
to the AirTouch 5. Since the AC Error Information Request uses the same ID as
the AC Error Information Message, a shared Encoder and Decoder are used.

This message is a sub-message of the Extended Message.
"""  # noqa: N999

import dataclasses

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import x1F_ext

MESSAGE_ID = 0xFF10


@dataclasses.dataclass
class AcErrorInformationMessage(comms.Message):
    """The Air-Conditioner Error Information Message."""

    ac_number: int
    """The AC to which the error applies."""
    error_info: str | None
    """The error information, or None if there is no error for this AC."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclasses.dataclass
class AcErrorInformationRequest(comms.Message):
    """Message to request AC Error Information."""

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
    """An encoder for the AC Error Information messages.

    The encoder handles both the AC Error Information Message and the AC Error
    Information Request since both have the same message ID.
    """

    @override
    def size(self, msg: AcErrorInformationMessage | AcErrorInformationRequest) -> int:
        if isinstance(msg, AcErrorInformationRequest):
            return 1  # AC Number only
        # Will result in the string being encoded twice, but we don't expect to
        # encode this message very often.
        if msg.error_info:
            return 2 + len(msg.error_info.encode())
        return 2

    @override
    def encode(
        self,
        _: x1F_ext.ExtendedMessageSubHeader,
        msg: AcErrorInformationMessage | AcErrorInformationRequest,
    ) -> bytes:
        buffer = bytearray()
        buffer.append(msg.ac_number & 0xFF)

        if isinstance(msg, AcErrorInformationMessage):
            if msg.error_info:
                error_string = msg.error_info.encode()
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
    """Decoder for the AC Error Information Message and Request.

    The decoder handles both the AC Error Information Message and the AC Error
    Information Request since they share a message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, hdr: x1F_ext.ExtendedMessageSubHeader
    ) -> comms.MessageDecodeResult[
        AcErrorInformationMessage | AcErrorInformationRequest
    ]:
        ac_number = buffer[0]
        # If the data only contains the AC number then this is a request
        if hdr.message_length == 1:
            return comms.MessageDecodeResult(
                message=AcErrorInformationRequest(ac_number=ac_number),
                remaining=buffer[1:],
            )

        # Otherwise this is the error information
        error_length = buffer[1]
        error_start = 2
        error_end = error_start + error_length

        error = None
        if error_length > 0:
            error = buffer[error_start:error_end].decode()

        return comms.MessageDecodeResult(
            message=AcErrorInformationMessage(ac_number=ac_number, error_info=error),
            remaining=buffer[error_end:],
        )
