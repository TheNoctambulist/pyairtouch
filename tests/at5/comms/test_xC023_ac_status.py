"""Tests for the AC Status message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at5.comms.xC0_ctrl_status import ControlStatusSubHeader
from pyairtouch.at5.comms.xC023_ac_status import (
    MESSAGE_ID,
    AcFanSpeed,
    AcMode,
    AcPowerState,
    AcStatusData,
    AcStatusDecoder,
    AcStatusEncoder,
    AcStatusMessage,
    AcStatusRequest,
)


def generate_header(
    message: AcStatusMessage | AcStatusRequest,
) -> ControlStatusSubHeader:
    """Construct a header for the AcStatusMessage"""
    encoder = AcStatusEncoder()
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
        (AcStatusRequest(), bytes(())),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.ON,
                        mode=AcMode.HEAT,
                        fan_speed=AcFanSpeed.LOW,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=22.0,
                        temperature=23.0,
                        error_code=0,
                    ),
                    AcStatusData(
                        ac_number=1,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.COOL,
                        fan_speed=AcFanSpeed.LOW,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=20.0,
                        temperature=24.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes(
                (
                    # AC 0
                    0x10,
                    0x12,
                    0x78,
                    0xC0,
                    0x02,
                    0xDA,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    # AC 1
                    0x01,
                    0x42,
                    0x64,
                    0xC0,
                    0x02,
                    0xE4,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                )
            ),
        ),
        #
        # Tests for AC Power State
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF_AWAY,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0b00100000, 0x00, 23, 0xC0, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.SLEEP,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0b01010000, 0x00, 23, 0xC0, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        #
        # Tests for AC Mode
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.FAN,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0b00110000, 23, 0xC0, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO_COOL,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0b10010000, 23, 0xC0, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        #
        # Tests for Fan Speed
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.MEDIUM,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0b00000011, 23, 0xC0, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.INTELLIGENT_AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0b00001001, 23, 0xC0, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        #
        # Tests for Turbo
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=True,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0x00, 23, 0b11001000, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        #
        # Tests for Bypass
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=True,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0x00, 23, 0b11000100, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        #
        # Tests for Spill
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=True,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0x00, 23, 0b11000010, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        #
        # Tests for Timer Set
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=True,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0,
                    )
                ]
            ),
            bytes((0x00, 0x00, 23, 0b11000001, 0x01, 0xF4, 0x00, 0x00, 0x00, 0x00)),
        ),
        #
        # Tests for error code
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        turbo_active=False,
                        bypass_active=False,
                        spill_active=False,
                        timer_set=False,
                        set_point=12.3,
                        temperature=0.0,
                        error_code=0xABCD,
                    )
                ]
            ),
            bytes((0x00, 0x00, 23, 0xC0, 0x01, 0xF4, 0xAB, 0xCD, 0x00, 0x00)),
        ),
    ],
)
class TestAcStatusEncoderDecoder:
    def test_encoder(
        self, message: AcStatusMessage | AcStatusRequest, message_buffer: bytes
    ) -> None:
        encoder = AcStatusEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self, message: AcStatusMessage | AcStatusRequest, message_buffer: bytes
    ) -> None:
        decoder = AcStatusDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
