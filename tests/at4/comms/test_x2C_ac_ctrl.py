"""Tests for the AC Control Message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.at4.comms.x2C_ac_ctrl import (
    MESSAGE_ID,
    AcControlDecoder,
    AcControlEncoder,
    AcControlMessage,
    AcFanSpeedControl,
    AcIncreaseDecrease,
    AcModeControl,
    AcPowerControl,
    AcSetPointValue,
)


def generate_header(message: AcControlMessage) -> At4Header:
    encoder = AcControlEncoder()
    return At4Header(
        to_address=0,
        from_address=0,
        packet_id=0,
        message_id=MESSAGE_ID,
        message_length=encoder.size(message),
    )


@pytest.mark.parametrize(
    argnames=["message", "message_buffer"],
    argvalues=[
        #
        # Example message from the interface specification.
        #
        (
            AcControlMessage(
                ac_number=1,
                power=AcPowerControl.TURN_OFF,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=None,
            ),
            bytes((0x81, 0xFF, 0x00, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.COOL,
                fan_speed=AcFanSpeedControl.AUTO,
                set_point_control=None,
            ),
            bytes((0x00, 0x40, 0x00, 0x00)),
        ),
        #
        # Power Control
        #
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.TOGGLE,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=None,
            ),
            bytes((0b01000000, 0xFF, 0x00, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.TURN_ON,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=None,
            ),
            bytes((0b11000000, 0xFF, 0x00, 0x00)),
        ),
        #
        # Mode Control
        #
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.AUTO,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=None,
            ),
            bytes((0x00, 0b00001111, 0x00, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.HEAT,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=None,
            ),
            bytes((0x00, 0b00011111, 0x00, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.DRY,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=None,
            ),
            bytes((0x00, 0b00101111, 0x00, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.FAN,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=None,
            ),
            bytes((0x00, 0b00111111, 0x00, 0x00)),
        ),
        #
        # Fan Speed Control
        #
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.QUIET,
                set_point_control=None,
            ),
            bytes((0x00, 0b11110001, 0x00, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.HIGH,
                set_point_control=None,
            ),
            bytes((0x00, 0b11110100, 0x00, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.TURBO,
                set_point_control=None,
            ),
            bytes((0x00, 0b11110110, 0x00, 0x00)),
        ),
        #
        # Set-point Control
        #
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=AcSetPointValue(23),
            ),
            bytes((0x00, 0xFF, 0b01000000 + 23, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=AcIncreaseDecrease.DECREASE,
            ),
            bytes((0x00, 0xFF, 0b10000000, 0x00)),
        ),
        (
            AcControlMessage(
                ac_number=0,
                power=AcPowerControl.UNCHANGED,
                mode=AcModeControl.UNCHANGED,
                fan_speed=AcFanSpeedControl.UNCHANGED,
                set_point_control=AcIncreaseDecrease.INCREASE,
            ),
            bytes((0x00, 0xFF, 0b11000000, 0x00)),
        ),
    ],
)
class TestAcControlEncoderDecoder:
    def test_encoder(self, message: AcControlMessage, message_buffer: bytes) -> None:
        encoder = AcControlEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(self, message: AcControlMessage, message_buffer: bytes) -> None:
        decoder = AcControlDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
