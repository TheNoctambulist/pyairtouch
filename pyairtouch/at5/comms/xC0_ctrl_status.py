"""Definition of the Control Command and Status Message (0xC0).

This is a variant message that can contain one of several sub message types. A
Control/Status sub-header is used to identify the sub message.

To ensure uniqueness and allow the sub-messages to be used alongside other
message objects, the ID of sub-messages is prefixed with 0xC0 (the ID of this
message).
"""  # noqa: N999

import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic, Protocol

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms.hdr import At5Header

MESSAGE_ID = 0xC0


@dataclass
class ControlStatusMessage(comms.Message, Generic[comms.Msg]):
    """A Control/Status Message.

    The Control/Status Message is just a wrapper for a child sub-message.
    """

    sub_message: comms.Msg

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class ControlStatusSubHeader(comms.Header):
    """The header for Control/Status sub-messages."""

    sub_message_id: int
    """ID of the sub-message."""
    non_repeat_length: int
    """Length (in bytes) of non-repeating fields."""
    repeat_length: int
    """Length (in bytes) of each group of repeated fields."""
    repeat_count: int
    """Number of repeated fields."""

    @override
    @property
    def message_id(self) -> int:
        return self.sub_message_id

    @override
    @property
    def message_length(self) -> int:
        """The length of the sub-message (in bytes).

        The length of the sub-message excluding this Control/Status sub-header.
        """
        return self.non_repeat_length + (self.repeat_count * self.repeat_length)


class ControlStatusSubEncoder(Protocol[comms.Msg_contra]):
    """Interface for a control/status sub-message encoder."""

    def non_repeat_size(self, message: comms.Msg_contra) -> int:
        """Size of the non-repeating part of the specified message in bytes."""

    def repeat_count(self, message: comms.Msg_contra) -> int:
        """Number of repeat sections included in the specified message."""

    def repeat_size(self, message: comms.Msg_contra) -> int:
        """Size of each repeat section in the specified message in bytes."""

    def encode(
        self, header: ControlStatusSubHeader, message: comms.Msg_contra
    ) -> bytes:
        """Encodes the specified messages into a bytes array."""


class UnsupportedControlStatusDecoder(
    comms.MessageDecoder[ControlStatusSubHeader, comms.UnsupportedMessage]
):
    """Message decoder for unsupported control and status messages."""

    @override
    def decode(
        self, buffer: bytes | bytearray, header: ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[comms.UnsupportedMessage]:
        data_length = (
            header.non_repeat_length + header.repeat_count * header.repeat_length
        )
        return comms.MessageDecodeResult(
            message=comms.UnsupportedMessage(
                unsupported_id=header.sub_message_id, raw_data=buffer[:data_length]
            ),
            remaining=buffer[data_length:],
        )


_SUB_HEADER_STRUCT = struct.Struct("!BxHHH")


class ControlStatusEncoder(comms.MessageEncoder[At5Header, ControlStatusMessage[Any]]):
    """Encodes Control/Status messages."""

    def __init__(self, encoder_map: Mapping[int, ControlStatusSubEncoder[Any]]) -> None:
        """Initialise the Control/Status Encoder.

        Args:
            encoder_map: Mapping from sub-message IDs to the corresponding encoder.
        """
        self._encoder_map = encoder_map

    def _sub_message_encoder(
        self, sub_message: comms.Msg
    ) -> ControlStatusSubEncoder[comms.Msg]:
        sub_message_encoder = self._encoder_map.get(sub_message.message_id)
        if not sub_message_encoder:
            raise NotImplementedError(
                f"Sub-message 0x{sub_message.message_id:02x} not implemented."
            )
        return sub_message_encoder

    @override
    def size(self, message: ControlStatusMessage[Any]) -> int:
        sub_message_encoder = self._sub_message_encoder(message.sub_message)
        non_repeat_size = sub_message_encoder.non_repeat_size(message.sub_message)
        repeat_count = sub_message_encoder.repeat_count(message.sub_message)
        total_repeat_size = repeat_count * sub_message_encoder.repeat_size(
            message.sub_message
        )
        return _SUB_HEADER_STRUCT.size + non_repeat_size + total_repeat_size

    @override
    def encode(self, _: At5Header, message: ControlStatusMessage[Any]) -> bytes:
        sub_message_encoder = self._sub_message_encoder(message.sub_message)

        sub_message_id = message.sub_message.message_id
        non_repeat_length = sub_message_encoder.non_repeat_size(message.sub_message)
        repeat_count = sub_message_encoder.repeat_count(message.sub_message)
        repeat_length = sub_message_encoder.repeat_size(message.sub_message)

        sub_header = ControlStatusSubHeader(
            sub_message_id=sub_message_id,
            non_repeat_length=non_repeat_length,
            repeat_count=repeat_count,
            repeat_length=repeat_length,
        )

        return _SUB_HEADER_STRUCT.pack(
            sub_message_id, non_repeat_length, repeat_length, repeat_count
        ) + sub_message_encoder.encode(sub_header, message.sub_message)


class ControlStatusDecoder(
    comms.MessageDecoder[At5Header, ControlStatusMessage[comms.Message]]
):
    """Decodes Control/Status messages."""

    _UNSUPPORTED_DECODER = UnsupportedControlStatusDecoder()

    def __init__(
        self,
        decoder_map: Mapping[
            int,
            comms.MessageDecoder[ControlStatusSubHeader, comms.Message],
        ],
    ) -> None:
        """Initialises the Control/Status Decoder.

        Args:
            decoder_map: Mapping from sub-message ID to the corresponding decoder.
        """
        self._decoder_map = decoder_map

    def _sub_message_decoder(
        self, sub_message_id: int
    ) -> comms.MessageDecoder[ControlStatusSubHeader, comms.Message]:
        sub_message_decoder = self._decoder_map.get(sub_message_id)
        if not sub_message_decoder:
            return ControlStatusDecoder._UNSUPPORTED_DECODER
        return sub_message_decoder

    @override
    def decode(
        self, buffer: bytes | bytearray, _: At5Header
    ) -> comms.MessageDecodeResult[ControlStatusMessage[comms.Message]]:
        """Decodes a control/status message from the buffer.

        The returned message will be one of the specific derived types of
        control and status messages.
        """
        (
            sub_message_id,
            non_repeat_length,
            repeat_length,
            repeat_count,
        ) = _SUB_HEADER_STRUCT.unpack_from(buffer)

        sub_header = ControlStatusSubHeader(
            sub_message_id, non_repeat_length, repeat_length, repeat_count
        )

        sub_message_decoder = self._sub_message_decoder(sub_message_id)

        sub_message_result = sub_message_decoder.decode(
            buffer[_SUB_HEADER_STRUCT.size :], sub_header
        )
        return comms.MessageDecodeResult(
            message=ControlStatusMessage(sub_message=sub_message_result.message),
            remaining=sub_message_result.remaining,
        )
