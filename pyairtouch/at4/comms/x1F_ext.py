"""Definiton of the Extended Message (0x1F).

Extended messages are used to obtain the available modes and fan speeds of the
ACs, and error information.
"""  # noqa: N999

import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.comms import MessageDecodeResult

MESSAGE_ID = 0x1F


@dataclass
class ExtendedMessageSubHeader:
    """Header for sub-messages within the Extended Message."""

    message_id: int
    """ID of the nexted sub-message."""

    message_length: int
    """Length of the sub-message in bytes.

    Excludes the bytes in the parent Extended Message (and AirTouch header).
    """


@dataclass
class ExtendedMessage(comms.Message, Generic[comms.Msg]):
    """The Extended Message."""

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
    ) -> MessageDecodeResult[comms.UnsupportedMessage]:
        return comms.MessageDecodeResult(
            message=comms.UnsupportedMessage(
                unsupported_id=hdr.message_id, raw_data=buffer[: hdr.message_length]
            ),
            remaining=buffer[hdr.message_length :],
        )


_EXTENDED_SUB_HDR_STRUCT = struct.Struct("!H")


class ExtendedMessageEncoder(comms.MessageEncoder[At4Header, ExtendedMessage[Any]]):
    """Encoder for extended messages."""

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
        self, sub_msg: comms.Msg
    ) -> comms.MessageEncoder[ExtendedMessageSubHeader, comms.Msg]:
        sub_msg_encoder = self._encoder_map.get(sub_msg.message_id)
        if not sub_msg_encoder:
            raise NotImplementedError(
                f"Encoding of sub-message 0x{sub_msg.message_id:02x} not implemented."
            )
        return sub_msg_encoder

    @override
    def size(self, msg: ExtendedMessage[comms.Msg]) -> int:
        sub_msg_encoder = self._sub_message_encoder(msg.sub_message)
        return _EXTENDED_SUB_HDR_STRUCT.size + sub_msg_encoder.size(msg.sub_message)

    @override
    def encode(self, hdr: At4Header, msg: ExtendedMessage[comms.Msg]) -> bytes:
        sub_msg = msg.sub_message
        sub_msg_encoder = self._sub_message_encoder(sub_msg)

        sub_message_id = sub_msg.message_id
        sub_message_length = sub_msg_encoder.size(sub_msg)

        sub_hdr = ExtendedMessageSubHeader(
            message_id=sub_message_id,
            message_length=sub_message_length,
        )

        return _EXTENDED_SUB_HDR_STRUCT.pack(sub_message_id) + sub_msg_encoder.encode(
            hdr=sub_hdr, msg=sub_msg
        )


class ExtendedMessageDecoder(
    comms.MessageDecoder[At4Header, ExtendedMessage[comms.Message]]
):
    """Decodes extended messages."""

    _UNSUPPORTED_DECODER = UnsupportedExtendedDecoder()

    def __init__(
        self,
        decoder_map: Mapping[
            int, comms.MessageDecoder[ExtendedMessageSubHeader, comms.Message]
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
        self, buffer: bytes | bytearray, hdr: At4Header
    ) -> MessageDecodeResult[ExtendedMessage[comms.Message]]:
        (sub_message_id,) = _EXTENDED_SUB_HDR_STRUCT.unpack_from(buffer)

        sub_hdr = ExtendedMessageSubHeader(
            message_id=sub_message_id,
            message_length=(hdr.message_length - _EXTENDED_SUB_HDR_STRUCT.size),
        )

        sub_msg_decoder = self._sub_msg_decoder(sub_message_id)
        sub_msg_result = sub_msg_decoder.decode(
            buffer=buffer[_EXTENDED_SUB_HDR_STRUCT.size :],
            hdr=sub_hdr,
        )
        return comms.MessageDecodeResult(
            message=ExtendedMessage(sub_message=sub_msg_result.message),
            remaining=sub_msg_result.remaining,
        )
