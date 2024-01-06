"""Tests for the Zone Control message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at5.comms.xC0_ctrl_status import ControlStatusSubHeader
from pyairtouch.at5.comms.xC020_zone_ctrl import (
    MESSAGE_ID,
    ZoneControlData,
    ZoneControlDecoder,
    ZoneControlEncoder,
    ZoneControlMessage,
    ZoneDamperControl,
    ZoneIncreaseDecrease,
    ZonePowerControl,
    ZoneSetPointControl,
)


def generate_header(message: ZoneControlMessage) -> ControlStatusSubHeader:
    """Construct a header for the ZoneControlMessage."""
    encoder = ZoneControlEncoder()
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
        # Example message from the protocol document.
        #
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=1,
                        zone_power=ZonePowerControl.TURN_OFF,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x01, 0x02, 0xFF, 0x00)),
        ),
        #
        # Testing zone number values
        #
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x00, 0b00000000, 0xFF, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=8,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x08, 0b00000000, 0xFF, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=15,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x0F, 0b00000000, 0xFF, 0x00)),
        ),
        #
        # Testing power state values (UNCHANGED case covered above)
        #
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.TOGGLE,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x00, 0b00000001, 0xFF, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.TURN_OFF,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x00, 0b00000010, 0xFF, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.TURN_ON,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x00, 0b00000011, 0xFF, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.TURBO,
                        zone_setting=None,
                    )
                ]
            ),
            bytes((0x00, 0b00000101, 0xFF, 0x00)),
        ),
        #
        # Testing Zone Settings (None case covered above)
        #
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=ZoneIncreaseDecrease.DECREASE,
                    )
                ]
            ),
            bytes((0x00, 0b01000000, 0xFF, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=ZoneIncreaseDecrease.INCREASE,
                    )
                ]
            ),
            bytes((0x00, 0b01100000, 0xFF, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=ZoneDamperControl(87),
                    )
                ]
            ),
            bytes((0x00, 0b10000000, 87, 0x00)),
        ),
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=ZoneSetPointControl(23),
                    )
                ]
            ),
            bytes((0x00, 0b10100000, 130, 0x00)),
        ),
        #
        # Testing multiple zones
        #
        (
            ZoneControlMessage(
                zone_control=[
                    ZoneControlData(
                        zone_number=0,
                        zone_power=ZonePowerControl.UNCHANGED,
                        zone_setting=ZoneSetPointControl(32),
                    ),
                    ZoneControlData(
                        zone_number=15,
                        zone_power=ZonePowerControl.TURN_ON,
                        zone_setting=None,
                    ),
                    ZoneControlData(
                        zone_number=3,
                        zone_power=ZonePowerControl.TURN_OFF,
                        zone_setting=ZoneIncreaseDecrease.INCREASE,
                    ),
                ]
            ),
            bytes(
                (
                    # Zone 0
                    0x00,
                    0b10100000,
                    220,
                    0x00,
                    # Zone 15
                    0x0F,
                    0b00000011,
                    0xFF,
                    0x00,
                    # Zone 3
                    0x03,
                    0b01100010,
                    0xFF,
                    0x00,
                )
            ),
        ),
    ],
)
class TestZoneControlEncoderDecoder:
    def test_encoder(self, message: ZoneControlMessage, message_buffer: bytes) -> None:
        encoder = ZoneControlEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(self, message: ZoneControlMessage, message_buffer: bytes) -> None:
        decoder = ZoneControlDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
