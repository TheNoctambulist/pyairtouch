import asyncio
from typing import cast
from unittest.mock import Mock

import pytest
from pyairtouch import ZoneControlMethod, ZoneControlMethodSwitching, comms
from pyairtouch.at5.api import At5Zone
from pyairtouch.at5.comms import hdr, registry
from pyairtouch.at5.comms.xC0_ctrl_status import (
    ControlStatusMessage,
    ControlStatusSubHeader,
)
from pyairtouch.at5.comms.xC020_zone_ctrl import (
    MESSAGE_ID,
    ZoneControlData,
    ZoneControlDecoder,
    ZoneControlEncoder,
    ZoneControlMessage,
    ZoneControlMethodCommand,
    ZoneDamperControl,
    ZonePowerControl,
    ZoneSetPointControl,
    ZoneSetting,
)
from pyairtouch.at5.comms.xC021_zone_status import (
    SensorBatteryStatus,
    ZonePowerState,
    ZoneStatusData,
    ZoneStatusMessage,
)
from pyairtouch.at5.comms.xC021_zone_status import (
    ZoneControlMethod as WireMethod,
)
from pyairtouch.comms.socket import AirTouchSocket

OFFICE_ZONE_ID = 4


def encode_frame(method: ZoneControlMethodCommand, packet_id: int) -> bytes:
    """Encode an Office method command as a complete AirTouch 5 frame."""
    message = ControlStatusMessage(
        ZoneControlMessage(
            [
                ZoneControlData(
                    zone_number=4,
                    zone_power=ZonePowerControl.UNCHANGED,
                    zone_setting=None,
                    control_method=method,
                )
            ]
        )
    )
    message_encoder = registry.INSTANCE.get_encoder(message.message_id)
    message_length = message_encoder.size(message)
    header = hdr.At5Header(
        to_address=hdr.ADDRESS_AIRTOUCH,
        from_address=hdr.ADDRESS_CLIENT,
        packet_id=packet_id,
        message_id=message.message_id,
        message_length=message_length,
    )
    encoded_header = registry.INSTANCE.header_encoder.encode(header)
    message_bytes = message_encoder.encode(header, message)
    checksum = registry.INSTANCE.checksum_calculator.calculate(
        encoded_header.checksum_data + message_bytes
    )
    return encoded_header.header_bytes + message_bytes + checksum


def decode_frame(
    frame: bytes,
) -> tuple[hdr.At5Header, ControlStatusMessage[comms.Message]]:
    """Decode and validate a complete AirTouch 5 application frame."""
    header_length = registry.INSTANCE.header_decoder.header_length
    header_result = registry.INSTANCE.header_decoder.decode(frame[:header_length])
    header_result.assert_complete()
    header = header_result.header
    message_start = header_length
    message_end = message_start + header.message_length
    message_bytes = frame[message_start:message_end]
    crc = frame[message_end:]
    assert registry.INSTANCE.checksum_calculator.validate(
        header_result.checksum_data + message_bytes, crc
    )
    message_result = registry.INSTANCE.get_decoder(header.message_id).decode(
        message_bytes, header
    )
    message_result.assert_complete()
    return header, cast("ControlStatusMessage[comms.Message]", message_result.message)


@pytest.mark.parametrize(
    ("before", "requested", "encoded"),
    [
        (WireMethod.DAMPER, ZoneControlMethod.TEMPERATURE, b"\x04\x18\xff\x00"),
        (WireMethod.TEMPERATURE, ZoneControlMethod.DAMPER, b"\x04\x10\xff\x00"),
    ],
)
def test_switch_changes_only_method_bits(
    before: WireMethod,
    requested: ZoneControlMethod,
    encoded: bytes,
) -> None:
    async def run() -> None:
        link = Mock(spec=AirTouchSocket)
        zone = At5Zone(4, "Office", link)
        assert isinstance(zone, ZoneControlMethodSwitching)
        setpoint = 23.0
        damper = 50
        await zone.update_zone_status(
            ZoneStatusData(
                zone_number=4,
                power_state=ZonePowerState.OFF,
                spill_active=False,
                control_method=before,
                has_sensor=True,
                battery_status=SensorBatteryStatus.NORMAL,
                temperature=24.0,
                damper_percentage=damper,
                set_point=setpoint,
            ),
        )
        current = zone.control_method
        await zone.set_control_method(current)
        link.send.assert_not_awaited()
        await zone.set_control_method(requested)
        link.send.assert_awaited_once()
        message = link.send.call_args.args[0].sub_message
        header = ControlStatusSubHeader(MESSAGE_ID, 0, 4, 1)
        assert ZoneControlEncoder().encode(header, message) == encoded
        assert ZoneControlDecoder().decode(encoded, header).message == message
        assert zone.control_method == current
        assert zone.target_temperature == setpoint
        assert zone.current_damper_percentage == damper

    asyncio.run(run())


def test_temperature_method_requires_sensor() -> None:
    link = Mock(spec=AirTouchSocket)
    zone = At5Zone(3, "Room", link)
    with pytest.raises(ValueError, match="requires a temperature sensor"):
        asyncio.run(zone.set_control_method(ZoneControlMethod.TEMPERATURE))
    link.send.assert_not_awaited()


def test_temperature_method_is_rejected_for_sensorless_temperature_status() -> None:
    async def run() -> None:
        link = Mock(spec=AirTouchSocket)
        zone = At5Zone(3, "Room", link)
        await zone.update_zone_status(
            ZoneStatusData(
                zone_number=3,
                power_state=ZonePowerState.OFF,
                spill_active=False,
                control_method=WireMethod.TEMPERATURE,
                has_sensor=False,
                battery_status=SensorBatteryStatus.NORMAL,
                temperature=None,
                damper_percentage=80,
                set_point=None,
            ),
        )
        with pytest.raises(ValueError, match="requires a temperature sensor"):
            await zone.set_control_method(ZoneControlMethod.TEMPERATURE)
        link.send.assert_not_awaited()

    asyncio.run(run())


def test_invalid_control_method_type_is_rejected() -> None:
    link = Mock(spec=AirTouchSocket)
    zone = At5Zone(3, "Room", link)
    invalid_method = cast("ZoneControlMethod", "temperature")
    with pytest.raises(TypeError, match="method must be a ZoneControlMethod"):
        asyncio.run(zone.set_control_method(invalid_method))
    link.send.assert_not_awaited()


@pytest.mark.parametrize(
    ("method", "setting", "power", "encoded"),
    [
        (
            ZoneControlMethodCommand.CHANGE,
            None,
            ZonePowerControl.TURN_OFF,
            b"\x03\x0a\xff\x00",
        ),
        (
            ZoneControlMethodCommand.DAMPER,
            ZoneDamperControl(80),
            ZonePowerControl.TURN_ON,
            b"\x03\x93\x50\x00",
        ),
        (
            ZoneControlMethodCommand.TEMPERATURE,
            ZoneSetPointControl(23.5),
            ZonePowerControl.TURBO,
            b"\x03\xbd\x87\x00",
        ),
    ],
)
def test_method_bits_preserve_setting_and_power(
    method: ZoneControlMethodCommand,
    setting: ZoneSetting,
    power: ZonePowerControl,
    encoded: bytes,
) -> None:
    message = ZoneControlMessage(
        [
            ZoneControlData(
                zone_number=3,
                zone_power=power,
                zone_setting=setting,
                control_method=method,
            )
        ]
    )
    header = ControlStatusSubHeader(MESSAGE_ID, 0, 4, 1)

    assert ZoneControlEncoder().encode(header, message) == encoded
    assert ZoneControlDecoder().decode(encoded, header).message == message


@pytest.mark.parametrize(
    ("method", "packet_id", "frame"),
    [
        (
            ZoneControlMethodCommand.DAMPER,
            0x3B,
            bytes.fromhex(
                "55 55 55 AB 00 00 00 18 00 18 55 55 55 AA "
                "80 B0 3B C0 00 0C 20 00 00 00 00 04 00 01 "
                "04 10 FF 00 EE 17"
            ),
        ),
        (
            ZoneControlMethodCommand.TEMPERATURE,
            0x3C,
            bytes.fromhex(
                "55 55 55 AB 00 00 00 18 00 18 55 55 55 AA "
                "80 B0 3C C0 00 0C 20 00 00 00 00 04 00 01 "
                "04 18 FF 00 1E D4"
            ),
        ),
    ],
)
def test_observed_office_commands_encode_complete_frame(
    method: ZoneControlMethodCommand, packet_id: int, frame: bytes
) -> None:
    """The observed Office commands reproduce the complete AirTouch frame."""
    assert encode_frame(method, packet_id) == frame


@pytest.mark.parametrize(
    ("frame", "packet_id", "method"),
    [
        (
            bytes.fromhex(
                "55 55 55 AB 00 00 00 4C 00 4C 55 55 55 AA "
                "B0 80 3B C0 00 40 21 00 00 00 00 08 00 07 "
                "00 64 78 80 02 DF 00 00 41 64 96 64 07 FF "
                "02 00 02 64 96 00 07 FF 00 00 03 64 96 32 "
                "07 FF 02 00 44 32 82 B2 02 E2 00 00 05 64 "
                "96 00 07 FF 00 00 06 64 8C 80 02 E8 00 00 FD ED"
            ),
            0x3B,
            WireMethod.DAMPER,
        ),
        (
            bytes.fromhex(
                "55 55 55 AB 00 00 00 4C 00 4C 55 55 55 AA "
                "B0 80 3C C0 00 40 21 00 00 00 00 08 00 07 "
                "00 64 78 80 02 DF 00 00 41 64 96 64 07 FF "
                "02 00 02 64 96 00 07 FF 00 00 03 64 96 32 "
                "07 FF 02 00 44 B2 82 B2 02 E2 00 00 05 64 "
                "96 00 07 FF 00 00 06 64 8C 80 02 E8 00 00 76 30"
            ),
            0x3C,
            WireMethod.TEMPERATURE,
        ),
    ],
)
def test_observed_office_status_frames_decode(
    frame: bytes, packet_id: int, method: WireMethod
) -> None:
    """The captured status frames validate and decode to the expected state."""
    header, message = decode_frame(frame)
    assert header.to_address == hdr.ADDRESS_CLIENT
    assert header.from_address == hdr.ADDRESS_AIRTOUCH
    assert header.packet_id == packet_id
    assert isinstance(message.sub_message, ZoneStatusMessage)
    office = next(
        zone for zone in message.sub_message.zones if zone.zone_number == OFFICE_ZONE_ID
    )
    assert office == ZoneStatusData(
        zone_number=4,
        power_state=ZonePowerState.ON,
        spill_active=False,
        control_method=method,
        has_sensor=True,
        battery_status=SensorBatteryStatus.NORMAL,
        temperature=23.8,
        damper_percentage=50,
        set_point=23.0,
    )
