"""Tests for the AC Control message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at5.comms.xC0_ctrl_status import ControlStatusSubHeader
from pyairtouch.at5.comms.xC022_ac_ctrl import (
    MESSAGE_ID,
    AcControlData,
    AcControlDecoder,
    AcControlEncoder,
    AcControlMessage,
    AcFanSpeedControl,
    AcModeControl,
    AcPowerControl,
)


def generate_header(message: AcControlMessage) -> ControlStatusSubHeader:
    """Construct a header for the AcControlMessage"""
    encoder = AcControlEncoder()
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
        # Example messages from the protocol document.
        #
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=1,
                        power=AcPowerControl.TURN_OFF,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x21, 0xFF, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.COOL,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    ),
                    AcControlData(
                        ac_number=1,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=26.0,
                    ),
                ]
            ),
            bytes((0x00, 0x4F, 0x00, 0xFF, 0x01, 0xFF, 0x40, 0xA0)),
        ),
        #
        # Testing Power Setting (UNCHANGED case covered previously)
        #
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.TOGGLE,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0b00010000, 0xFF, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.TURN_OFF,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0b00100000, 0xFF, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.TURN_ON,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0b00110000, 0xFF, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.SET_TO_AWAY,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0b01000000, 0xFF, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.SET_TO_SLEEP,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0b01010000, 0xFF, 0x00, 0xFF)),
        ),
        #
        # Test AC number
        #
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=7,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0b00000111, 0xFF, 0x00, 0xFF)),
        ),
        #
        # Test AC Mode (UNCHANGED case covered previously)
        #
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.AUTO,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b00001111, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.HEAT,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b00011111, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.DRY,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b00101111, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.FAN,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b00111111, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.COOL,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b01001111, 0x00, 0xFF)),
        ),
        #
        # Test AC Fan Speed (UNCHANGED case covered previously)
        # Not full coverage because the enum is large.
        #
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.AUTO,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b11110000, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.QUIET,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b11110001, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.HIGH,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b11110100, 0x00, 0xFF)),
        ),
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.INTELLIGENT_AUTO,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0b11111000, 0x00, 0xFF)),
        ),
        #
        # Test Set Point Control (UNCHANGED case covered previously)
        #
        (
            AcControlMessage(
                ac_control=[
                    AcControlData(
                        ac_number=0,
                        power=AcPowerControl.UNCHANGED,
                        mode=AcModeControl.UNCHANGED,
                        fan_speed=AcFanSpeedControl.UNCHANGED,
                        set_point=23.4,
                    )
                ]
            ),
            bytes((0x00, 0xFF, 0x40, 134)),
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
