"""Tests for the Zone Status message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at5.comms.xC0_ctrl_status import ControlStatusSubHeader
from pyairtouch.at5.comms.xC021_zone_status import (
    MESSAGE_ID,
    SensorBatteryStatus,
    ZoneControlMethod,
    ZonePowerState,
    ZoneStatusData,
    ZoneStatusDecoder,
    ZoneStatusEncoder,
    ZoneStatusMessage,
    ZoneStatusRequest,
)


def generate_header(
    message: ZoneStatusMessage | ZoneStatusRequest,
) -> ControlStatusSubHeader:
    """Construct a header for the ZoneStatusMessage"""
    encoder = ZoneStatusEncoder()
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
        (ZoneStatusRequest(), bytes(())),
        (
            ZoneStatusMessage(
                zones=[
                    ZoneStatusData(
                        zone_number=0,
                        power_state=ZonePowerState.ON,
                        spill_active=False,
                        control_method=ZoneControlMethod.TEMPERATURE,
                        has_sensor=True,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=24.3,
                        damper_percentage=0,
                        set_point=25.0,
                    ),
                    ZoneStatusData(
                        zone_number=1,
                        power_state=ZonePowerState.OFF,
                        spill_active=False,
                        control_method=ZoneControlMethod.DAMPER,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=100,
                        set_point=None,
                    ),
                ]
            ),
            bytes(
                (
                    # Zone 1
                    0x40,
                    0x80,
                    0x96,
                    0x80,
                    0x02,
                    0xE7,
                    0x00,
                    0x00,
                    # Zone 2
                    0x01,
                    0x64,
                    0xFF,
                    0x00,
                    0x07,
                    0xFF,
                    0x00,
                    0x00,
                )
            ),
        ),
        #
        # Testing power state values (ON and OFF covered above)
        #
        (
            ZoneStatusMessage(
                zones=[
                    ZoneStatusData(
                        zone_number=0,
                        power_state=ZonePowerState.TURBO,
                        spill_active=False,
                        control_method=ZoneControlMethod.DAMPER,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    )
                ]
            ),
            bytes((0b11000000, 0x00, 0xFF, 0x00, 0x07, 0xFF, 0x00, 0x00)),
        ),
        #
        # Testing Spill Active
        #
        (
            ZoneStatusMessage(
                zones=[
                    ZoneStatusData(
                        zone_number=0,
                        power_state=ZonePowerState.OFF,
                        spill_active=True,
                        control_method=ZoneControlMethod.DAMPER,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0x00, 0xFF, 0x00, 0x07, 0xFF, 0b00000010, 0x00)),
        ),
        #
        # Testing Low Battery
        #
        (
            ZoneStatusMessage(
                zones=[
                    ZoneStatusData(
                        zone_number=0,
                        power_state=ZonePowerState.OFF,
                        spill_active=False,
                        control_method=ZoneControlMethod.DAMPER,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.LOW,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    )
                ]
            ),
            bytes((0x00, 0x00, 0xFF, 0x00, 0x07, 0xFF, 0b00000001, 0x00)),
        ),
    ],
)
class TestZoneStatusEncoderDecoder:
    def test_encoder(
        self, message: ZoneStatusMessage | ZoneStatusRequest, message_buffer: bytes
    ) -> None:
        encoder = ZoneStatusEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self, message: ZoneStatusMessage | ZoneStatusRequest, message_buffer: bytes
    ) -> None:
        decoder = ZoneStatusDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
