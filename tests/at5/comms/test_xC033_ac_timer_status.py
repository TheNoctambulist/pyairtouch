"""Tests for the AC Timer Status message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at5.comms.xC0_ctrl_status import ControlStatusSubHeader
from pyairtouch.at5.comms.xC033_ac_timer_status import (
    MESSAGE_ID,
    AcTimerState,
    AcTimerStatusData,
    AcTimerStatusDecoder,
    AcTimerStatusEncoder,
    AcTimerStatusMessage,
    AcTimerStatusRequest,
)


def generate_header(
    message: AcTimerStatusMessage | AcTimerStatusRequest,
) -> ControlStatusSubHeader:
    """Construct a header for the AC Timer Status Message or Request."""
    encoder = AcTimerStatusEncoder()
    return ControlStatusSubHeader(
        sub_message_id=MESSAGE_ID,
        non_repeat_length=encoder.non_repeat_size(message),
        repeat_length=encoder.repeat_size(message),
        repeat_count=encoder.repeat_count(message),
    )


@pytest.mark.parametrize(
    argnames=["message", "message_buffer"],
    argvalues=[
        #
        # Request
        #
        (AcTimerStatusRequest(), bytes(())),
        #
        # Both timers disabled
        #
        (
            AcTimerStatusMessage(
                ac_timer_status=[
                    AcTimerStatusData(
                        ac_number=1,
                        on_timer=AcTimerState(
                            disabled=True,
                            hour=2,
                            minute=3,
                        ),
                        off_timer=AcTimerState(
                            disabled=True,
                            hour=4,
                            minute=5,
                        ),
                    )
                ]
            ),
            b"\x01\x82\x03\x84\x05\x00\x00\x00\x00",
        ),
        #
        # On-timer enabled
        #
        (
            AcTimerStatusMessage(
                ac_timer_status=[
                    AcTimerStatusData(
                        ac_number=1,
                        on_timer=AcTimerState(
                            disabled=False,
                            hour=2,
                            minute=3,
                        ),
                        off_timer=AcTimerState(
                            disabled=True,
                            hour=4,
                            minute=5,
                        ),
                    )
                ]
            ),
            b"\x01\x02\x03\x84\x05\x00\x00\x00\x00",
        ),
        #
        # Off timer enabled
        #
        (
            AcTimerStatusMessage(
                ac_timer_status=[
                    AcTimerStatusData(
                        ac_number=1,
                        on_timer=AcTimerState(
                            disabled=True,
                            hour=2,
                            minute=3,
                        ),
                        off_timer=AcTimerState(
                            disabled=False,
                            hour=4,
                            minute=5,
                        ),
                    )
                ]
            ),
            b"\x01\x82\x03\x04\x05\x00\x00\x00\x00",
        ),
        #
        # Multiple ACs
        #
        (
            AcTimerStatusMessage(
                ac_timer_status=[
                    AcTimerStatusData(
                        ac_number=1,
                        on_timer=AcTimerState(
                            disabled=False,
                            hour=2,
                            minute=3,
                        ),
                        off_timer=AcTimerState(
                            disabled=True,
                            hour=4,
                            minute=5,
                        ),
                    ),
                    AcTimerStatusData(
                        ac_number=2,
                        on_timer=AcTimerState(
                            disabled=True,
                            hour=2,
                            minute=3,
                        ),
                        off_timer=AcTimerState(
                            disabled=False,
                            hour=23,
                            minute=59,
                        ),
                    ),
                    AcTimerStatusData(
                        ac_number=4,
                        on_timer=AcTimerState(
                            disabled=False,
                            hour=0,
                            minute=0,
                        ),
                        off_timer=AcTimerState(
                            disabled=False,
                            hour=23,
                            minute=59,
                        ),
                    ),
                ]
            ),
            (
                b"\x01\x02\x03\x84\x05\x00\x00\x00\x00"  # AC 1
                b"\x02\x82\x03\x17\x3b\x00\x00\x00\x00"  # AC 2
                b"\x04\x00\x00\x17\x3b\x00\x00\x00\x00"  # AC 4
            ),
        ),
    ],
)
class TestAcTimerStatusStatusEncoderDecoder:
    def test_encoder(
        self,
        message: AcTimerStatusMessage | AcTimerStatusRequest,
        message_buffer: bytes,
    ) -> None:
        encoder = AcTimerStatusEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self,
        message: AcTimerStatusMessage | AcTimerStatusRequest,
        message_buffer: bytes,
    ) -> None:
        decoder = AcTimerStatusDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
