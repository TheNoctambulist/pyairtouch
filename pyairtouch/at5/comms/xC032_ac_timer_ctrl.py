"""Definition of the AC Timer Control Message (0xC032).

The AC Timer Control message is used to activate or de-activate Quick Timers for
an AC.

This message is a sub-message of the Control Command and Status Message.

The AC Timer Control Message is not documented in the API. The definition of
this message has been reverse engineered.
"""  # noqa: N999

from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import xC0_ctrl_status, xC033_ac_timer_status

MESSAGE_ID = 0x32

# Aliases for re-used Timer Status types.
AcTimerState = xC033_ac_timer_status.AcTimerState
AcTimerControlData = xC033_ac_timer_status.AcTimerStatusData


@dataclass
class AcTimerControlMessage(xC033_ac_timer_status.AcTimerStatusMessage):
    """The AC Timer Control Message.

    The contents of this message are identical to the AC Timer Status Message,
    so that is extended here to allow re-use of the encoding and decoding
    logic.
    """

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


AcTimerControlEncoder = xC033_ac_timer_status.AcTimerStatusEncoder
"""Encoder for the AC Timer Control Message.

No custom encoding logic is required."""


class AcTimerControlDecoder(
    comms.MessageDecoder[
        xC0_ctrl_status.ControlStatusSubHeader,
        AcTimerControlMessage,
    ]
):
    """Decoder for the AC Timer Control Message."""

    def __init__(self) -> None:
        """Initialise the AcTimerControlDecoder."""
        self._ac_timer_status_decoder = xC033_ac_timer_status.AcTimerStatusDecoder()

    @override
    def decode(
        self, buffer: bytes | bytearray, header: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[AcTimerControlMessage]:
        result = self._ac_timer_status_decoder.decode(buffer, header)
        if not isinstance(result.message, xC033_ac_timer_status.AcTimerStatusMessage):
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
