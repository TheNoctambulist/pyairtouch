"""Definition of the AC Timer Status Message (0x37).

AC Timer Status messages report the current setting for Quick Timers. A received
message always includes timer status for four air-conditioners, it is up to the
user to filter out data for invalid air-conditioners.

The AC Timer Status message will be sent automatically whenever the AC Timer
Status changes. An AC Timer Status Request can also be sent to request current
AC Timer Status from the AirTouch 4.

Since the AC Timer Status Request uses the same message ID as the AC Timer
Status Message, a shared Encoder and Decoder are used.

The AC Timer Status Message is not documented in the API. The definition of this
message has been reverse engineered.
"""

import struct
from collections.abc import Sequence
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.comms import MessageDecodeResult, encoding

MESSAGE_ID = 0x37


@dataclass
class AcTimerState:
    """Represents the state of an AC timer."""

    disabled: bool
    """Whether or not the timer is disabled."""

    hour: int
    minute: int
    """The hour and minute of the day at which the timer will be active.

    Values should be ignored if the timer is disabled."""


@dataclass
class AcTimerStatusData:
    """Timer Status data for a single air-conditioner."""

    ac_number: int
    on_timer: AcTimerState
    off_timer: AcTimerState


@dataclass
class AcTimerStatusMessage(comms.Message):
    """The AC Timer Status Message."""

    ac_timer_status: Sequence[AcTimerStatusData]
    """The timer status for each AC.

    When processing a received message, entries may be included in the sequence
    for invalid air-conditioners IDs. IDs should be cross checked before
    processing the values."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class AcTimerStatusRequest(comms.Message):
    """Request for AC Timer Status."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_TIMER_STATE_STRUCT = struct.Struct("!BBxx")
# On and Off Timer for each AC
_TIMER_STATUS_REPEAT_SIZE = 2 * _TIMER_STATE_STRUCT.size


class AcTimerStatusEncoder(
    comms.MessageEncoder[At4Header, AcTimerStatusMessage | AcTimerStatusRequest]
):
    """Encoder for the AC Timer Status Message.

    A common encoder is used for messages and requests because they share the
    same message ID.
    """

    @override
    def size(self, message: AcTimerStatusMessage | AcTimerStatusRequest) -> int:
        if isinstance(message, AcTimerStatusRequest):
            return 0  # AC Timer Status Request is empty
        # Message is fixed at 4 ACs
        return 4 * _TIMER_STATUS_REPEAT_SIZE

    @override
    def encode(
        self, header: At4Header, message: AcTimerStatusMessage | AcTimerStatusRequest
    ) -> bytes:
        if isinstance(message, AcTimerStatusRequest):
            return b""

        # Message is fixed at 4 ACs length with implicit AC numbering.
        # Any ACs that are not included in the intial message will be left zeroed out.
        buffer = bytearray(self.size(message))
        for ac_timer_status in message.ac_timer_status:
            on_offset = ac_timer_status.ac_number * _TIMER_STATUS_REPEAT_SIZE
            self._pack_timer_state(buffer, on_offset, ac_timer_status.on_timer)
            off_offset = on_offset + _TIMER_STATE_STRUCT.size
            self._pack_timer_state(buffer, off_offset, ac_timer_status.off_timer)

        return buffer

    def _pack_timer_state(
        self, buffer: bytes, offset: int, timer_state: AcTimerState
    ) -> None:
        encoded_disabled = encoding.bool_to_bit(timer_state.disabled, 7)
        encoded_hour = timer_state.hour & 0x1F
        encoded_minute = timer_state.minute & 0x3F
        b1 = encoded_disabled + encoded_hour
        _TIMER_STATE_STRUCT.pack_into(buffer, offset, b1, encoded_minute)


class AcTimerStatusDecoder(
    comms.MessageDecoder[At4Header, AcTimerStatusMessage | AcTimerStatusRequest]
):
    """Decoder for the AC Timer Status Message and Request."""

    @override
    def decode(
        self, buffer: bytes | bytearray, header: At4Header
    ) -> MessageDecodeResult[AcTimerStatusMessage | AcTimerStatusRequest]:
        # If there is no data in the message this is a request for AC Timer Status
        if header.message_length == 0:
            return comms.MessageDecodeResult(
                message=AcTimerStatusRequest(),
                remaining=buffer,
            )

        # Otherwise decode status information for each AC:
        if (header.message_length % _TIMER_STATUS_REPEAT_SIZE) != 0:
            raise comms.DecodeError(
                f"Message length ({header.message_length}) is not "
                f"a multiple of AC Timer Status size ({_TIMER_STATUS_REPEAT_SIZE})."
            )

        ac_timer_status: list[AcTimerStatusData] = []

        # The AC Number is implicitly derived from the index into the repeating
        # structure of the message.
        for ac_number in range(header.message_length // _TIMER_STATUS_REPEAT_SIZE):
            on_offset = ac_number * _TIMER_STATUS_REPEAT_SIZE
            off_offset = on_offset + _TIMER_STATE_STRUCT.size
            ac_timer_status.append(
                AcTimerStatusData(
                    ac_number=ac_number,
                    on_timer=self._decode_timer_state(buffer, on_offset),
                    off_timer=self._decode_timer_state(buffer, off_offset),
                )
            )

        return comms.MessageDecodeResult(
            message=AcTimerStatusMessage(ac_timer_status),
            remaining=buffer[header.message_length :],
        )

    def _decode_timer_state(
        self, buffer: bytes | bytearray, offset: int
    ) -> AcTimerState:
        (b1, encoded_minute) = _TIMER_STATE_STRUCT.unpack_from(buffer, offset)

        return AcTimerState(
            disabled=encoding.bit_to_bool(b1, 7),
            hour=(b1 & 0x1F),
            minute=(encoded_minute & 0x3F),
        )
