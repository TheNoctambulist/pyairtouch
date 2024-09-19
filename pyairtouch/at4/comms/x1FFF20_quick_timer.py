"""Definition of the Quick Timer Message (0x1FFF20).

The Quick Timer message allows for automatically turning an AC on/off a set
number of hours/minutes in the future.

The Quick Timer message is not part of the official API. Contents of this
message have been reverse engineered.

This message is a sub-message of the Extended Message.
"""  # noqa: N999

import datetime
import enum
import struct
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import x1F_ext

MESSAGE_ID = 0xFF20


class TimerType(enum.Enum):
    """Type of the Quick Timer."""

    OFF_TIMER = 0
    ON_TIMER = 1


@dataclass
class QuickTimerMessage(comms.Message):
    """The Quick Timer message."""

    ac_number: int
    """The Air-Conditioner to set the timer for."""

    timer_type: TimerType
    duration: datetime.timedelta
    """The duration of the timer. Resolution is to the nearest minute."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BBBB")


class QuickTimerEncoder(
    comms.MessageEncoder[x1F_ext.ExtendedMessageSubHeader, QuickTimerMessage]
):
    """Encoder for the Quick Timer Message."""

    @override
    def size(self, message: QuickTimerMessage) -> int:
        return _STRUCT.size

    @override
    def encode(
        self,
        _: x1F_ext.ExtendedMessageSubHeader,
        message: QuickTimerMessage,
    ) -> bytes:
        hours, minutes = self._encode_duration(message.duration)
        return _STRUCT.pack(
            message.ac_number,
            self._encode_timer_type(message.timer_type),
            hours,
            minutes,
        )

    def _encode_timer_type(self, timer_type: TimerType) -> int:
        return timer_type.value & 0xFF

    def _encode_duration(self, duration: datetime.timedelta) -> tuple[int, int]:
        """Encode the timer durataion into an hours and minutes tuple."""
        hours, seconds = divmod(duration.total_seconds(), 3600)
        # Testing suggests the message supports a quick timer setting of up to
        # 255 hours in this message, however the resulting timer will be modulo
        # 24 hours. To provide intuitive behaviour even if the durataion is
        # larger than 255 hours, we replicate the modulo 24 behaviour here.
        hours = hours % 24
        minutes = seconds // 60
        return int(hours) & 0xFF, int(minutes) & 0xFF


class QuickTimerDecoder(
    comms.MessageDecoder[x1F_ext.ExtendedMessageSubHeader, QuickTimerMessage]
):
    """Decoder for the Quick Timer Message."""

    @override
    def decode(
        self, buffer: bytes | bytearray, _: x1F_ext.ExtendedMessageSubHeader
    ) -> comms.MessageDecodeResult[QuickTimerMessage]:
        (
            ac_number,
            timer_type_raw,
            hours,
            minutes,
        ) = _STRUCT.unpack_from(buffer)

        return comms.MessageDecodeResult(
            message=QuickTimerMessage(
                ac_number=ac_number,
                timer_type=self._decode_timer_type(timer_type_raw),
                duration=self._decode_duration(hours, minutes),
            ),
            remaining=buffer[_STRUCT.size :],
        )

    def _decode_timer_type(self, timer_type_raw: int) -> TimerType:
        return TimerType(timer_type_raw)

    def _decode_duration(self, hours: int, minutes: int) -> datetime.timedelta:
        return datetime.timedelta(hours=hours, minutes=minutes)
