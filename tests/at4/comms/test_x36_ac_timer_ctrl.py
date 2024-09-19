"""Tests for the AC Timer Status message encoder and decoder."""

import pytest
from pyairtouch.at4.comms import x37_ac_timer_status
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.at4.comms.x36_ac_timer_ctrl import (
    MESSAGE_ID,
    AcTimerControlDecoder,
    AcTimerControlEncoder,
    AcTimerControlMessage,
)
from pyairtouch.at4.comms.x37_ac_timer_status import (
    AcTimerState,
    AcTimerStatusData,
)


def generate_header(
    message: AcTimerControlMessage,
) -> At4Header:
    """Construct a header for the AC Timer Status Message or Request."""
    # The encoder is not used for message length calculations here to allow
    # testing of a scenario where the message is not the fixed size observed
    # during reverse engineering. For other messages, the AirTouch 4 supports
    # variable length messages, so it has been supported in the decoder for
    # increased flexibility.
    message_length = (
        len(message.ac_timer_status) * x37_ac_timer_status._TIMER_STATUS_REPEAT_SIZE  # noqa: SLF001
    )
    return At4Header(
        to_address=0,
        from_address=0,
        packet_id=0,
        message_id=MESSAGE_ID,
        message_length=message_length,
    )


_common_parametrizations = [
    #
    # Request
    #
    (
        AcTimerControlMessage(
            ac_timer_status=[
                #
                # Both timers disabled
                #
                AcTimerStatusData(
                    ac_number=0,
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
                ),
                #
                # On-timer enabled
                #
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
                #
                # Off timer enabled
                #
                AcTimerStatusData(
                    ac_number=2,
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
                ),
                AcTimerStatusData(
                    ac_number=3,
                    on_timer=AcTimerState(
                        disabled=False,
                        hour=0,
                        minute=0,
                    ),
                    off_timer=AcTimerState(
                        disabled=False,
                        hour=0,
                        minute=0,
                    ),
                ),
            ]
        ),
        (
            b"\x82\x03\x00\x00\x84\x05\x00\x00"
            b"\x02\x03\x00\x00\x84\x05\x00\x00"
            b"\x82\x03\x00\x00\x04\x05\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        ),
    ),
]


class TestAcTimerStatusStatusEncoderDecoder:
    @pytest.mark.parametrize(
        argnames=["message", "message_buffer"],
        argvalues=[
            *_common_parametrizations,
            #
            # Less than four ACs
            #
            (
                AcTimerControlMessage(
                    ac_timer_status=[
                        AcTimerStatusData(
                            ac_number=0,
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
                        ),
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
                    ]
                ),
                (
                    b"\x82\x03\x00\x00\x84\x05\x00\x00"
                    b"\x02\x03\x00\x00\x84\x05\x00\x00"
                    b"\x00\x00\x00\x00\x00\x00\x00\x00"
                    b"\x00\x00\x00\x00\x00\x00\x00\x00"
                ),
            ),
        ],
    )
    def test_encoder(
        self,
        message: AcTimerControlMessage,
        message_buffer: bytes,
    ) -> None:
        encoder = AcTimerControlEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    @pytest.mark.parametrize(
        argnames=["message", "message_buffer"],
        argvalues=[
            *_common_parametrizations,
            #
            # Less than four ACs
            #
            (
                AcTimerControlMessage(
                    ac_timer_status=[
                        AcTimerStatusData(
                            ac_number=0,
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
                        ),
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
                    ]
                ),
                (
                    b"\x82\x03\x00\x00\x84\x05\x00\x00"
                    b"\x02\x03\x00\x00\x84\x05\x00\x00"
                ),
            ),
        ],
    )
    def test_decoder(
        self,
        message: AcTimerControlMessage,
        message_buffer: bytes,
    ) -> None:
        decoder = AcTimerControlDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
