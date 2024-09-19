"""Tests the encoder and decoder for the Quick Timer Message."""  # noqa: N999

import datetime

import pytest
from pyairtouch.at5.comms import x1F_ext
from pyairtouch.at5.comms.x1FFF49_quick_timer import (
    MESSAGE_ID,
    QuickTimerDecoder,
    QuickTimerEncoder,
    QuickTimerMessage,
    TimerType,
)


def generate_header(message: QuickTimerMessage) -> x1F_ext.ExtendedMessageSubHeader:
    encoder = QuickTimerEncoder()
    return x1F_ext.ExtendedMessageSubHeader(
        message_id=MESSAGE_ID, message_length=encoder.size(message)
    )


_common_parametrizations = [
    #
    # Off-Timer
    #
    (
        QuickTimerMessage(
            ac_number=1,
            timer_type=TimerType.OFF_TIMER,
            duration=datetime.timedelta(hours=2, minutes=3),
        ),
        b"\x01\x00\x02\x03",
    ),
    #
    # On-Timer
    #
    (
        QuickTimerMessage(
            ac_number=1,
            timer_type=TimerType.ON_TIMER,
            duration=datetime.timedelta(hours=2, minutes=3),
        ),
        b"\x01\x01\x02\x03",
    ),
    #
    # AC Number
    #
    (
        QuickTimerMessage(
            ac_number=9,
            timer_type=TimerType.ON_TIMER,
            duration=datetime.timedelta(hours=2, minutes=3),
        ),
        b"\x09\x01\x02\x03",
    ),
]


class TestQuickTimerEncoderDecoder:
    @pytest.mark.parametrize(
        argnames=["message", "message_buffer"],
        argvalues=[
            *_common_parametrizations,
            #
            # Large Duration
            #
            (
                QuickTimerMessage(
                    ac_number=1,
                    timer_type=TimerType.ON_TIMER,
                    duration=datetime.timedelta(hours=248, minutes=59),
                ),
                b"\x01\x01\x08\x3b",  # Wrapped to modulo 24 hours
            ),
        ],
    )
    def test_encoder(
        self,
        message: QuickTimerMessage,
        message_buffer: bytes,
    ) -> None:
        encoder = QuickTimerEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    @pytest.mark.parametrize(
        argnames=["message", "message_buffer"],
        argvalues=[
            *_common_parametrizations,
            #
            # Large Duration
            #
            (
                QuickTimerMessage(
                    ac_number=1,
                    timer_type=TimerType.ON_TIMER,
                    duration=datetime.timedelta(hours=255, minutes=59),
                ),
                b"\x01\x01\xff\x3b",  # Test decode of >24 hours
            ),
        ],
    )
    def test_decoder(
        self,
        message: QuickTimerMessage,
        message_buffer: bytes,
    ) -> None:
        decoder = QuickTimerDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
