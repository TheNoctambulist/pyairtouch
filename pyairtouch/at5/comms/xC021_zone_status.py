"""Definition of the Zone Status Message (0xC021).

Zone Status messages report the power state, set point/damper, and other status
of a zone in the AirTouch system. Each message can include status for one or
more zones.

The Zone Status message will be sent automatically whenever the Zone Status changes.
A Zone Status Request can also be sent to request current zone status from the
AirTouch 5.

Since the Zone Status Request uses the same message ID as the Zone Status Message, a
shared Encoder and Decoder are used.

This message is a sub-message of the Control Command and Status Message.
"""  # noqa: N999

import enum
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import utils, xC0_ctrl_status
from pyairtouch.comms import encoding

MESSAGE_ID = 0x21


class ZonePowerState(enum.Enum):
    """The current zone power state."""

    OFF = 0
    ON = 1
    TURBO = 3


class ZoneControlMethod(enum.Enum):
    """The current zone control method."""

    DAMPER = 0
    TEMPERATURE = 1


class SensorBatteryStatus(enum.Enum):
    """Battery status of the zone's temperature sensor."""

    NORMAL = 0
    LOW = 1


@dataclass
class ZoneStatusData:
    """Status data for a zone in the AirTouch system."""

    zone_number: int
    power_state: ZonePowerState
    spill_active: bool

    control_method: ZoneControlMethod

    has_sensor: bool
    battery_status: SensorBatteryStatus
    temperature: Optional[float]
    """The current zone temperature in degrees Celsius.

    None if no temperature sensor is installed.
    """

    damper_percentage: int
    """The current damper opening percentage. Range [0, 100]."""

    set_point: Optional[float]
    """The zone's temperature setpoint in degrees Celsius.

    None if the zone doesn't have a sensor and no set point is defined.
    """


@dataclass
class ZoneStatusMessage(comms.Message):
    """The Zone Status Message."""

    zones: Sequence[ZoneStatusData]

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class ZoneStatusRequest(comms.Message):
    """Request for Zone Status Data."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BBBBHBx")

_INVALID_SET_POINT = 0xFF
_INVALID_TEMPERATURE = 0x07FF  # Based on the examples.
_MAXIMUM_TEMPERATURE = 150.0  # From the communication protocol.


class ZoneStatusEncoder(
    xC0_ctrl_status.ControlStatusSubEncoder[ZoneStatusMessage | ZoneStatusRequest]
):
    """Encoder for the Zone Status Message and Zone Status Request.

    Handles both the message and the request since they have the same message ID.
    """

    @override
    def non_repeat_size(self, _: ZoneStatusMessage | ZoneStatusRequest) -> int:
        # No non-repeating data
        return 0

    @override
    def repeat_count(self, message: ZoneStatusMessage | ZoneStatusRequest) -> int:
        if isinstance(message, ZoneStatusRequest):
            return 0
        return len(message.zones)

    @override
    def repeat_size(self, message: ZoneStatusMessage | ZoneStatusRequest) -> int:
        if isinstance(message, ZoneStatusRequest):
            return 0
        return _STRUCT.size

    @override
    def encode(
        self,
        _: xC0_ctrl_status.ControlStatusSubHeader,
        message: ZoneStatusMessage | ZoneStatusRequest,
    ) -> bytes:
        if isinstance(message, ZoneStatusRequest):
            # ZoneStatusRequest has no content
            return b""

        buffer = bytearray()
        for zone in message.zones:
            encoded_zone_number = self._encode_zone_number(zone.zone_number)
            encoded_power_state = self._encode_power_state(zone.power_state)
            encoded_control_method = self._encode_control_method(zone.control_method)
            encoded_open_percentage = self._encode_open_percentage(
                zone.damper_percentage
            )
            encoded_set_point = self._encode_set_point(zone.set_point)
            encoded_has_sensor = self._encode_has_sensor(zone.has_sensor)
            encoded_temperature = self._encode_temperature(zone.temperature)
            encoded_spill_active = self._encode_spill_active(zone.spill_active)
            encoded_low_battery = self._encode_low_battery(zone.battery_status)

            b1 = encoded_zone_number + encoded_power_state
            b2 = encoded_control_method + encoded_open_percentage
            b7 = encoded_spill_active + encoded_low_battery
            buffer.extend(
                _STRUCT.pack(
                    b1,
                    b2,
                    encoded_set_point,
                    encoded_has_sensor,
                    encoded_temperature,
                    b7,
                )
            )
        return buffer

    def _encode_zone_number(self, zone_number: int) -> int:
        return zone_number & 0x3F

    def _encode_power_state(self, power_state: ZonePowerState) -> int:
        return power_state.value << 6

    def _encode_control_method(self, control_method: ZoneControlMethod) -> int:
        return control_method.value << 7

    def _encode_open_percentage(self, damper_percentage: int) -> int:
        return damper_percentage & 0x7F

    def _encode_set_point(self, set_point: Optional[float]) -> int:
        if set_point:
            return utils.encode_set_point(set_point)
        return _INVALID_SET_POINT

    def _encode_has_sensor(self, has_sensor: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(has_sensor, 7)

    def _encode_temperature(self, temperature: Optional[float]) -> int:
        if temperature:
            return utils.encode_temperature(temperature)
        return _INVALID_TEMPERATURE

    def _encode_spill_active(self, spill_active: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(spill_active, 1)

    def _encode_low_battery(self, battery_status: SensorBatteryStatus) -> int:
        return battery_status.value


class ZoneStatusDecoder(
    comms.MessageDecoder[
        xC0_ctrl_status.ControlStatusSubHeader, ZoneStatusMessage | ZoneStatusRequest
    ]
):
    """Decoder for the Zone Status Message and Request.

    Handles both the message and the request because they share the same ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[ZoneStatusMessage | ZoneStatusRequest]:
        # If there is no data in the message, this is a request for Zone Status
        if header.repeat_length == 0 and header.repeat_count == 0:
            return comms.MessageDecodeResult(
                message=ZoneStatusRequest(),
                remaining=buffer,
            )

        # Otherwise decode Zone Status information for each zone:
        if header.repeat_length != _STRUCT.size:
            raise comms.DecodeError(
                f"Header repeat_length ({header.repeat_length}) != "
                f"Zone Status Data size ({_STRUCT.size})"
            )

        zones: list[ZoneStatusData] = []
        for _ in range(header.repeat_count):
            (
                b1,
                b2,
                set_point_raw,
                b4,
                temp_raw,
                b7,
            ) = _STRUCT.unpack_from(buffer)
            has_sensor = self._decode_has_sensor(b4)
            zones.append(
                ZoneStatusData(
                    zone_number=self._decode_zone_number(b1),
                    power_state=self._decode_power_state(b1),
                    spill_active=self._decode_spill_active(b7),
                    control_method=self._decode_control_method(b2),
                    has_sensor=has_sensor,
                    battery_status=self._decode_battery_status(b7),
                    temperature=self._decode_temperature(has_sensor, temp_raw),
                    damper_percentage=self._decode_damper_percentage(b2),
                    set_point=self._decode_set_point(set_point_raw),
                )
            )
            buffer = buffer[header.repeat_length :]

        return comms.MessageDecodeResult(
            message=ZoneStatusMessage(zones=zones),
            remaining=buffer,
        )

    def _decode_zone_number(self, byte1: int) -> int:
        return byte1 & 0x3F

    def _decode_power_state(self, byte1: int) -> ZonePowerState:
        return ZonePowerState((byte1 & 0xC0) >> 6)

    def _decode_spill_active(self, byte7: int) -> bool:
        return encoding.bit_to_bool(byte7, 1)

    def _decode_control_method(self, byte2: int) -> ZoneControlMethod:
        return ZoneControlMethod((byte2 & 0x80) >> 7)

    def _decode_has_sensor(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 7)

    def _decode_temperature(self, has_sensor: bool, temp_raw: int) -> Optional[float]:  # noqa: FBT001
        decoded_temperature = utils.decode_temperature(temp_raw)
        if not has_sensor or decoded_temperature > _MAXIMUM_TEMPERATURE:
            return None
        return decoded_temperature

    def _decode_battery_status(self, byte7: int) -> SensorBatteryStatus:
        return SensorBatteryStatus(byte7 & 0x01)

    def _decode_damper_percentage(self, b2: int) -> int:
        return b2 & 0x7F

    def _decode_set_point(self, set_point_raw: int) -> Optional[float]:
        if set_point_raw == _INVALID_SET_POINT:
            return None
        return utils.decode_set_point(set_point_raw)
