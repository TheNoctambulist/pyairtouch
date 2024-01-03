"""Tests for the AC Status encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.at4.comms.x2D_ac_status import (
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


def generate_header(message: AcStatusMessage | AcStatusRequest) -> At4Header:
    encoder = AcStatusEncoder()
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
        # Examples from the interface specification.
        #
        (
            AcStatusRequest(),
            b"",
        ),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.ON,
                        mode=AcMode.COOL,
                        fan_speed=AcFanSpeed.LOW,
                        spill_active=False,
                        timer_set=False,
                        set_point=26,
                        temperature=28.0,
                        error_code=0,
                    ),
                    AcStatusData(
                        ac_number=1,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        spill_active=False,
                        timer_set=False,
                        set_point=26,
                        temperature=28.0,
                        error_code=0xFFFE,
                    ),
                ]
            ),
            bytes(
                (
                    # AC 0
                    0x40,
                    0x42,
                    0x1A,
                    0x00,
                    0x61,
                    0x80,
                    0x00,
                    0x00,
                    # AC 1
                    0x01,
                    0x00,
                    0x1A,
                    0x00,
                    0x61,
                    0x80,
                    0xFF,
                    0xFE,
                )
            ),
        ),
        #
        # AC Mode
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        spill_active=False,
                        timer_set=False,
                        set_point=26,
                        temperature=28.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes((0x00, 0b00000000, 0x1A, 0x00, 0x61, 0x80, 0x00, 0x00)),
        ),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.FAN,
                        fan_speed=AcFanSpeed.AUTO,
                        spill_active=False,
                        timer_set=False,
                        set_point=26,
                        temperature=28.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes((0x00, 0b00110000, 0x1A, 0x00, 0x61, 0x80, 0x00, 0x00)),
        ),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO_COOL,
                        fan_speed=AcFanSpeed.AUTO,
                        spill_active=False,
                        timer_set=False,
                        set_point=26,
                        temperature=28.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes((0x00, 0b10010000, 0x1A, 0x00, 0x61, 0x80, 0x00, 0x00)),
        ),
        #
        # Fan Speed
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.MEDIUM,
                        spill_active=False,
                        timer_set=False,
                        set_point=0,
                        temperature=28.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes((0x00, 0b00000011, 0x00, 0x00, 0x61, 0x80, 0x00, 0x00)),
        ),
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.TURBO,
                        spill_active=False,
                        timer_set=False,
                        set_point=0,
                        temperature=28.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes((0x00, 0b00000110, 0x00, 0x00, 0x61, 0x80, 0x00, 0x00)),
        ),
        #
        # Spill Active
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        spill_active=True,
                        timer_set=False,
                        set_point=0,
                        temperature=28.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes((0x00, 0x00, 0b10000000, 0x00, 0x61, 0x80, 0x00, 0x00)),
        ),
        #
        # Timer Set
        #
        (
            AcStatusMessage(
                ac_status=[
                    AcStatusData(
                        ac_number=0,
                        power_state=AcPowerState.OFF,
                        mode=AcMode.AUTO,
                        fan_speed=AcFanSpeed.AUTO,
                        spill_active=False,
                        timer_set=True,
                        set_point=0,
                        temperature=28.0,
                        error_code=0,
                    ),
                ]
            ),
            bytes((0x00, 0x00, 0b01000000, 0x00, 0x61, 0x80, 0x00, 0x00)),
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
