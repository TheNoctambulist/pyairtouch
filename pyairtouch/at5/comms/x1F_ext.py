"""Definition of the Extended Message (0x1F).

Extended messages are used to obtain the available modes and fan speeds of the
ACs, the names of zones, and error information.

When sending an extended message the to address should be 0x90. When receiving
an extended message the from address will be 0x90.

This is a variant message that can contain one of several sub message types. An
Extended sub-header is used to idenfity the sub message.

To ensure uniqueness and allow sub-messages to be used alongside other message
objects, the ID of sub-messages is prefixed with 0x1F (the ID of this message).
"""  # noqa: N999

import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms.hdr import At5Header

MESSAGE_ID = 0x1F


@dataclass
class ExtendedMessageSubHeader:
    """Header for sub-messages within the Extended Message."""

    message_id: int
    """Id of the nested sub-message."""
    message_length: int
    """Length of the sub-message in bytes.

    Excludes the bytes in the parent Extended Message (and AirTouch header).
    """


@dataclass
class ExtendedMessage(comms.Message, Generic[comms.Msg]):
    """An AirTouch 5 extended message."""

    sub_message: comms.Msg

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


class UnsupportedExtendedDecoder(
    comms.MessageDecoder[ExtendedMessageSubHeader, comms.UnsupportedMessage]
):
    """An implementation of the message decoder for unsupported extended messages."""

    @override
    def decode(
        self, buffer: bytes | bytearray, header: ExtendedMessageSubHeader
    ) -> comms.MessageDecodeResult[comms.UnsupportedMessage]:
        return comms.MessageDecodeResult(
            message=comms.UnsupportedMessage(
                unsupported_id=header.message_id,
                raw_data=buffer[: header.message_length],
            ),
            remaining=buffer[header.message_length :],
        )


_SUB_HEADER_STRUCT = struct.Struct("!H")


class ExtendedMessageEncoder(comms.MessageEncoder[At5Header, ExtendedMessage[Any]]):
    """Encodes extended messages."""

    def __init__(
        self,
        encoder_map: Mapping[int, comms.MessageEncoder[ExtendedMessageSubHeader, Any]],
    ) -> None:
        """Initialise the ExtendedMessageEncoder.

        Args:
            encoder_map: a mapping from sub-message IDs to corresponding
                sub-message encoders.
        """
        self._encoder_map = encoder_map

    def _sub_message_encoder(
        self, sub_message: comms.Msg
    ) -> comms.MessageEncoder[ExtendedMessageSubHeader, comms.Msg]:
        sub_message_encoder = self._encoder_map.get(sub_message.message_id)
        if not sub_message_encoder:
            raise NotImplementedError(
                f"Sub-message 0x{sub_message.message_id:02x} not implemented."
            )
        return sub_message_encoder

    @override
    def size(self, message: ExtendedMessage[comms.Msg]) -> int:
        sub_message_encoder = self._sub_message_encoder(message.sub_message)
        return _SUB_HEADER_STRUCT.size + sub_message_encoder.size(message.sub_message)

    @override
    def encode(self, _: At5Header, message: ExtendedMessage[comms.Msg]) -> bytes:
        sub_message = message.sub_message
        sub_message_encoder = self._sub_message_encoder(message.sub_message)

        sub_message_id = message.sub_message.message_id
        sub_message_length = sub_message_encoder.size(sub_message)

        sub_header = ExtendedMessageSubHeader(
            message_id=sub_message_id, message_length=sub_message_length
        )

        return _SUB_HEADER_STRUCT.pack(sub_message_id) + sub_message_encoder.encode(
            sub_header, sub_message
        )


class ExtendedMessageDecoder(
    comms.MessageDecoder[At5Header, ExtendedMessage[comms.Message]]
):
    """Decodes extended messages."""

    _UNSUPPORTED_DECODER = UnsupportedExtendedDecoder()

    def __init__(
        self,
        decoder_map: Mapping[
            int,
            comms.MessageDecoder[ExtendedMessageSubHeader, comms.Message],
        ],
    ) -> None:
        """Initialise the ExtendedMessageDecoder.

        Args:
            decoder_map: A mapping from sub-message IDs to their message decoders.
        """
        self._decoder_map = decoder_map

    def _sub_message_decoder(
        self, sub_message_id: int
    ) -> comms.MessageDecoder[ExtendedMessageSubHeader, comms.Message]:
        sub_message_decoder = self._decoder_map.get(sub_message_id)
        if not sub_message_decoder:
            return ExtendedMessageDecoder._UNSUPPORTED_DECODER
        return sub_message_decoder

    @override
    def decode(
        self, buffer: bytes | bytearray, header: At5Header
    ) -> comms.MessageDecodeResult[ExtendedMessage[comms.Message]]:
        (sub_message_id,) = _SUB_HEADER_STRUCT.unpack_from(buffer)

        sub_header = ExtendedMessageSubHeader(
            message_id=sub_message_id,
            message_length=(header.message_length - _SUB_HEADER_STRUCT.size),
        )

        sub_message_decoder = self._sub_message_decoder(sub_message_id)
        sub_message_result = sub_message_decoder.decode(
            buffer[_SUB_HEADER_STRUCT.size :], sub_header
        )
        return comms.MessageDecodeResult(
            message=ExtendedMessage(sub_message=sub_message_result.message),
            remaining=sub_message_result.remaining,
        )
