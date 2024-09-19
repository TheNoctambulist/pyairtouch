"""Definition of the AC Timer Status Message (0xC030).

AC Timer Status messages report the current setting for Quick Timers. Each
message can include status for one or more ACs (in a multi-AC AirTouch system).

The AC Timer Status message will be sent automatically whenever the AC Timer
Status changes. An AC Timer Status Request can also be sent to request current
AC status from the AirTouch 5.

Since the AC Timer Status Request uses the same message ID as the AC Timer
Status Message, a shared Encoder and Decoder are used.

This message is a sub-message of the Control Command and Status Message.

The AC Timer Status Message is not documented in the API. The definition of this
message has been reverse engineered.
"""  # noqa: N999

import logging
import struct
from collections.abc import Sequence
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import xC0_ctrl_status
from pyairtouch.comms import encoding

MESSAGE_ID = 0x33

_LOGGER = logging.getLogger(__name__)


@dataclass
class AcTimerState:
    """The state of an AC timer."""

    disabled: bool
    """Whether the timer is disabled."""

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


_TIMER_STATE_STRUCT = struct.Struct("!BB")

# There are four trailing 0-bytes observed at the end of every message.
_PADDING_BYTES = b"\x00\x00\x00\x00"
_PADDING_BYTES_SIZE = len(_PADDING_BYTES)
# AC Number + On-Timer + Off-Timer + Padding
_TIMER_STATUS_REPEAT_SIZE = 1 + 2 * _TIMER_STATE_STRUCT.size + _PADDING_BYTES_SIZE


class AcTimerStatusEncoder(
    xC0_ctrl_status.ControlStatusSubEncoder[AcTimerStatusMessage | AcTimerStatusRequest]
):
    """Encoder for the AC Timer Status Message and Request.

    Handles both the message and request since they have the same message ID.
    """

    @override
    def non_repeat_size(
        self, message: AcTimerStatusMessage | AcTimerStatusRequest
    ) -> int:
        # No non-repeating data
        return 0

    @override
    def repeat_count(self, message: AcTimerStatusMessage | AcTimerStatusRequest) -> int:
        if isinstance(message, AcTimerStatusRequest):
            return 0
        return len(message.ac_timer_status)

    @override
    def repeat_size(self, message: AcTimerStatusMessage | AcTimerStatusRequest) -> int:
        if isinstance(message, AcTimerStatusRequest):
            return 0
        return _TIMER_STATUS_REPEAT_SIZE

    @override
    def encode(
        self,
        header: xC0_ctrl_status.ControlStatusSubHeader,
        message: AcTimerStatusMessage | AcTimerStatusRequest,
    ) -> bytes:
        if isinstance(message, AcTimerStatusRequest):
            # AcTimerStatusRequest has no content
            return b""

        buffer = bytearray()
        for ac in message.ac_timer_status:
            buffer.append(ac.ac_number)
            buffer.extend(self._encode_timer_state(ac.on_timer))
            buffer.extend(self._encode_timer_state(ac.off_timer))
            buffer.extend(_PADDING_BYTES)

        return buffer

    def _encode_timer_state(self, timer_state: AcTimerState) -> bytes:
        encoded_active = encoding.bool_to_bit(timer_state.disabled, 7)
        encoded_hour = timer_state.hour & 0x1F
        encoded_minute = timer_state.minute & 0x3F
        b1 = encoded_active + encoded_hour

        return _TIMER_STATE_STRUCT.pack(b1, encoded_minute)


class AcTimerStatusDecoder(
    comms.MessageDecoder[
        xC0_ctrl_status.ControlStatusSubHeader,
        AcTimerStatusMessage | AcTimerStatusRequest,
    ]
):
    """Decoder for the AC Timer Status Message and Request."""

    def __init__(self) -> None:
        """Initialise the ACTimerStatusDecoder."""
        # Avoid repeated logging of message length mismatches if the console has
        # an upgraded protocol.
        self._mismatch_logged = False

    @override
    def decode(
        self, buffer: bytes | bytearray, header: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[AcTimerStatusMessage | AcTimerStatusRequest]:
        # If there is no data, this is a request for AC Timer Status
        if header.repeat_count == 0 and header.repeat_length == 0:
            return comms.MessageDecodeResult(
                message=AcTimerStatusRequest(),
                remaining=buffer,
            )

        # Otherwise decode AC Timer Status information for each AC:
        if header.repeat_length < _TIMER_STATUS_REPEAT_SIZE:
            raise comms.DecodeError(
                f"Header repeat length ({header.repeat_length}) < "
                f"AC Timer Status Data size ({_TIMER_STATUS_REPEAT_SIZE})"
            )

        if (
            header.repeat_length != _TIMER_STATUS_REPEAT_SIZE
            and not self._mismatch_logged
        ):
            _LOGGER.info(
                "Header repeat_length (%d) != AC Timer Status Data size (%d). "
                "Ignoring extra bytes",
                header.repeat_length,
                _TIMER_STATUS_REPEAT_SIZE,
            )
            self._mismatch_logged = True

        acs: list[AcTimerStatusData] = []
        for _ in range(header.repeat_count):
            acs.append(
                AcTimerStatusData(
                    ac_number=buffer[0],
                    on_timer=self._decode_timer_state(buffer[1:]),
                    off_timer=self._decode_timer_state(
                        buffer[1 + _TIMER_STATE_STRUCT.size :]
                    ),
                )
            )
            buffer = buffer[header.repeat_length :]

        return comms.MessageDecodeResult(
            message=AcTimerStatusMessage(acs),
            remaining=buffer,
        )

    def _decode_timer_state(self, buffer: bytes | bytearray) -> AcTimerState:
        (b1, encoded_minute) = _TIMER_STATE_STRUCT.unpack_from(buffer)
        return AcTimerState(
            disabled=encoding.bit_to_bool(b1, 7),
            hour=(b1 & 0x1F),
            minute=(encoded_minute & 0x3F),
        )
