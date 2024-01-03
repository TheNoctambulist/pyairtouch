"""Tests for the Group Status Message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.at4.comms.x2B_group_status import (
    MESSAGE_ID,
    GroupControlMethod,
    GroupPowerState,
    GroupStatusData,
    GroupStatusDecoder,
    GroupStatusEncoder,
    GroupStatusMessage,
    GroupStatusRequest,
    SensorBatteryStatus,
)


def generate_header(message: GroupStatusMessage | GroupStatusRequest) -> At4Header:
    encoder = GroupStatusEncoder()
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
        # Example messages from the interface specification.
        #
        (
            GroupStatusRequest(),
            b"",
        ),
        (
            GroupStatusMessage(
                groups=[
                    GroupStatusData(
                        group_number=0,
                        power_state=GroupPowerState.ON,
                        control_method=GroupControlMethod.DAMPER,
                        spill_active=False,
                        supports_turbo=False,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=100,
                        set_point=None,
                    ),
                    GroupStatusData(
                        group_number=1,
                        power_state=GroupPowerState.ON,
                        control_method=GroupControlMethod.TEMPERATURE,
                        spill_active=False,
                        supports_turbo=False,
                        has_sensor=True,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=28.0,
                        damper_percentage=100,
                        set_point=26,
                    ),
                ]
            ),
            bytes(
                (
                    # Group 1
                    0x40,
                    0x64,
                    0x00,
                    0x00,
                    0xFF,
                    0x00,
                    # Group 2
                    0x41,
                    0xE4,
                    0x1A,
                    0x80,
                    0x61,
                    0x80,
                )
            ),
        ),
        #
        # Power State
        #
        (
            GroupStatusMessage(
                groups=[
                    GroupStatusData(
                        group_number=0,
                        power_state=GroupPowerState.OFF,
                        control_method=GroupControlMethod.DAMPER,
                        spill_active=False,
                        supports_turbo=False,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    ),
                ]
            ),
            bytes((0b00000000, 0x00, 0x00, 0x00, 0xFF, 0x00)),
        ),
        (
            GroupStatusMessage(
                groups=[
                    GroupStatusData(
                        group_number=0,
                        power_state=GroupPowerState.TURBO,
                        control_method=GroupControlMethod.DAMPER,
                        spill_active=False,
                        supports_turbo=False,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    ),
                ]
            ),
            bytes((0b11000000, 0x00, 0x00, 0x00, 0xFF, 0x00)),
        ),
        #
        # Batter Low
        #
        (
            GroupStatusMessage(
                groups=[
                    GroupStatusData(
                        group_number=0,
                        power_state=GroupPowerState.OFF,
                        control_method=GroupControlMethod.DAMPER,
                        spill_active=False,
                        supports_turbo=False,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.LOW,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    ),
                ]
            ),
            bytes((0x00, 0x00, 0b10000000, 0x00, 0xFF, 0x00)),
        ),
        #
        # Supports Turbo
        #
        (
            GroupStatusMessage(
                groups=[
                    GroupStatusData(
                        group_number=0,
                        power_state=GroupPowerState.OFF,
                        control_method=GroupControlMethod.DAMPER,
                        spill_active=False,
                        supports_turbo=True,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    ),
                ]
            ),
            bytes((0x00, 0x00, 0b01000000, 0x00, 0xFF, 0x00)),
        ),
        #
        # Spill Active
        #
        (
            GroupStatusMessage(
                groups=[
                    GroupStatusData(
                        group_number=0,
                        power_state=GroupPowerState.OFF,
                        control_method=GroupControlMethod.DAMPER,
                        spill_active=True,
                        supports_turbo=False,
                        has_sensor=False,
                        battery_status=SensorBatteryStatus.NORMAL,
                        temperature=None,
                        damper_percentage=0,
                        set_point=None,
                    ),
                ]
            ),
            bytes((0x00, 0x00, 0x00, 0x00, 0xFF, 0b00010000)),
        ),
    ],
)
class TestGroupStatusEncoderDecoder:
    def test_encoder(
        self, message: GroupStatusMessage | GroupStatusRequest, message_buffer: bytes
    ) -> None:
        encoder = GroupStatusEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self, message: GroupStatusMessage | GroupStatusRequest, message_buffer: bytes
    ) -> None:
        decoder = GroupStatusDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
