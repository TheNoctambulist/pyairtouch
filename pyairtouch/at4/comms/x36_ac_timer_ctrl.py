"""Definition of the AC Timer Control Message (0x37).

The AC Timer Control message is used to activate or de-activate Quick Timers for
ACs.

The AC Timer Control Message is not documented in the API. The definition of
this message has been reverse engineered.
"""

from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import x37_ac_timer_status
from pyairtouch.at4.comms.hdr import At4Header

MESSAGE_ID = 0x36

# Aliases for re-used Timer Status types.
AcTimerState = x37_ac_timer_status.AcTimerState
AcTimerControlData = x37_ac_timer_status.AcTimerStatusData


@dataclass
class AcTimerControlMessage(x37_ac_timer_status.AcTimerStatusMessage):
    """The AC Timer Control Message.

    The contents of this message are identical to the AC Timer Status Message,
    so that is extended here to allow re-use of encoding and decoding logic.
    """

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


AcTimerControlEncoder = x37_ac_timer_status.AcTimerStatusEncoder
"""Encoder for the AC Timer Control Message.

No custom encoding logic is required."""


class AcTimerControlDecoder(comms.MessageDecoder[At4Header, AcTimerControlMessage]):
    """Decoder for the AC Timer Control Message."""

    def __init__(self) -> None:
        """Initialise the AcTimerControlDecoder."""
        self._ac_timer_status_decoder = x37_ac_timer_status.AcTimerStatusDecoder()

    @override
    def decode(
        self, buffer: bytes | bytearray, header: At4Header
    ) -> comms.MessageDecodeResult[AcTimerControlMessage]:
        result = self._ac_timer_status_decoder.decode(buffer, header)
        if not isinstance(result.message, x37_ac_timer_status.AcTimerStatusMessage):
            # This should never occur.
            raise comms.DecodeError(
                "Empty message not supported for AC Timer Control Message."
            )

        return comms.MessageDecodeResult(
            message=AcTimerControlMessage(
                ac_timer_status=result.message.ac_timer_status
            ),
            remaining=result.remaining,
        )
