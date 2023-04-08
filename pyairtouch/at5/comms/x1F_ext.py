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

import dataclasses
import struct
from collections.abc import Mapping
from typing import Any, Generic

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms.hdr import At5Header

MESSAGE_ID = 0x1F


@dataclasses.dataclass
class ExtendedMessageSubHeader:
    """Header for sub-messages within the Extended Message."""

    message_id: int
    """Id of the nested sub-message."""
    message_length: int
    """Length of the sub-message in bytes.

    Excludes the byes in the parent Extended Message (and AirTouch header).
    """


@dataclasses.dataclass
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
        self, buffer: bytes | bytearray, hdr: ExtendedMessageSubHeader
    ) -> comms.MessageDecodeResult[comms.UnsupportedMessage]:
        return comms.MessageDecodeResult(
            message=comms.UnsupportedMessage(
                unsupported_id=hdr.message_id, raw_data=buffer[: hdr.message_length]
            ),
            remaining=buffer[hdr.message_length :],
        )


_EXTENDED_SUB_HDR_STRUCT = struct.Struct("!H")


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

    def _sub_msg_encoder(
        self, sub_msg: comms.Msg
    ) -> comms.MessageEncoder[ExtendedMessageSubHeader, comms.Msg]:
        sub_msg_encoder = self._encoder_map.get(sub_msg.message_id)
        if not sub_msg_encoder:
            raise NotImplementedError(
                f"Encoding of sub-message 0x{sub_msg.message_id:02x} not implemented."
            )
        return sub_msg_encoder

    @override
    def size(self, msg: ExtendedMessage[Any]) -> int:
        sub_msg_encoder = self._sub_msg_encoder(msg.sub_message)
        return _EXTENDED_SUB_HDR_STRUCT.size + sub_msg_encoder.size(msg.sub_message)

    @override
    def encode(self, _: At5Header, msg: ExtendedMessage[Any]) -> bytes:
        sub_msg = msg.sub_message
        sub_msg_encoder = self._sub_msg_encoder(msg.sub_message)

        message_id = msg.message_id
        sub_message_id = msg.sub_message.message_id
        sub_message_length = sub_msg_encoder.size(sub_msg)

        sub_hdr = ExtendedMessageSubHeader(
            message_id=message_id, message_length=sub_message_length
        )

        return _EXTENDED_SUB_HDR_STRUCT.pack(sub_message_id) + sub_msg_encoder.encode(
            sub_hdr, sub_msg
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

    def _sub_msg_decoder(
        self, sub_message_id: int
    ) -> comms.MessageDecoder[ExtendedMessageSubHeader, comms.Message]:
        sub_msg_decoder = self._decoder_map.get(sub_message_id)
        if not sub_msg_decoder:
            return ExtendedMessageDecoder._UNSUPPORTED_DECODER
        return sub_msg_decoder

    @override
    def decode(
        self, buffer: bytes | bytearray, hdr: At5Header
    ) -> comms.MessageDecodeResult[ExtendedMessage[comms.Message]]:
        (sub_message_id,) = _EXTENDED_SUB_HDR_STRUCT.unpack_from(buffer)

        sub_hdr = ExtendedMessageSubHeader(
            message_id=sub_message_id,
            message_length=(hdr.message_length - _EXTENDED_SUB_HDR_STRUCT.size),
        )

        sub_msg_decoder = self._sub_msg_decoder(sub_message_id)
        sub_msg_result = sub_msg_decoder.decode(
            buffer[_EXTENDED_SUB_HDR_STRUCT.size :], sub_hdr
        )
        return comms.MessageDecodeResult(
            message=ExtendedMessage(sub_message=sub_msg_result.message),
            remaining=sub_msg_result.remaining,
        )
