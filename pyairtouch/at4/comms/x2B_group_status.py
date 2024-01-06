"""Definition of the Group Status Message (0x2B).

Group Status messages report the power state, set-point/damper and other status
of a zone in the AirTouch system. Each message can include status for one or
more zones.

The Group Status message will be sent automatically whenever the Group Status
changes. A Group Status Request can also be sent to request current Group Status
from the AirTouch 4.
"""  # noqa: N999

import enum
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import utils
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.comms import MessageDecodeResult, encoding

MESSAGE_ID = 0x2B


class GroupPowerState(enum.Enum):
    """The current group power state."""

    OFF = 0
    ON = 1
    TURBO = 3


class GroupControlMethod(enum.Enum):
    """The current group control method."""

    DAMPER = 0
    TEMPERATURE = 1


class SensorBatteryStatus(enum.Enum):
    """Battery status of the group's temperature sensor."""

    NORMAL = 0
    LOW = 1


@dataclass
class GroupStatusData:
    """Status data for a group in the AirTouch system."""

    group_number: int
    power_state: GroupPowerState
    control_method: GroupControlMethod
    spill_active: bool

    supports_turbo: bool
    has_sensor: bool
    battery_status: SensorBatteryStatus

    temperature: Optional[float]
    """The current group temperature in degrees Celsius.

    None if no temperature sensor is installed.
    """

    damper_percentage: int
    """The current damper opening percentage. Range [0, 100]."""

    set_point: Optional[int]
    """The group's temperature set-point in degrees Celsius.

    None if no temperature sensor is installed.
    """


@dataclass
class GroupStatusMessage(comms.Message):
    """The Group Status Message."""

    groups: Sequence[GroupStatusData]

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class GroupStatusRequest(comms.Message):
    """Request for Group Status Data."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BBBBH")

# Magic numbers from the interface specification.
_TEMP_UNAVAILABLE = 0xFF00  # encoded
_INVALID_SETPOINT = 0x00  # Based on example messages.


class GroupStatusEncoder(
    comms.MessageEncoder[At4Header, GroupStatusMessage | GroupStatusRequest]
):
    """Encoder for the Group Status Message and Request.

    Handles both the message and the request because they have the same message ID.
    """

    @override
    def size(self, message: GroupStatusMessage | GroupStatusRequest) -> int:
        match message:
            case GroupStatusRequest():
                # The request is an empty message
                return 0
            case GroupStatusMessage():
                return _STRUCT.size * len(message.groups)

    @override
    def encode(
        self, header: At4Header, message: GroupStatusMessage | GroupStatusRequest
    ) -> bytes:
        if isinstance(message, GroupStatusRequest):
            # The GroupStatusRequest is an empty message.
            return b""

        buffer = bytearray()
        for group in message.groups:
            encoded_group_number = self._encode_group_number(group.group_number)
            encoded_power_state = self._encode_power_state(group.power_state)
            encoded_control_method = self._encode_control_method(group.control_method)
            encoded_open_percentage = self._encode_open_percentage(
                group.damper_percentage
            )
            encoded_set_point = self._encode_set_point(group.set_point)
            encoded_has_sensor = self._encode_has_sensor(group.has_sensor)
            encoded_supports_turbo = self._encode_supports_turbo(group.supports_turbo)
            encoded_temperature = self._encode_temperature(group.temperature)
            encoded_spill_active = self._encode_spill_active(group.spill_active)
            encoded_low_battery = self._encode_low_battery(group.battery_status)

            b1 = encoded_power_state + encoded_group_number
            b2 = encoded_control_method + encoded_open_percentage
            b3 = encoded_low_battery + encoded_supports_turbo + encoded_set_point
            b56 = encoded_temperature + encoded_spill_active
            buffer.extend(_STRUCT.pack(b1, b2, b3, encoded_has_sensor, b56))

        return buffer

    def _encode_group_number(self, group_number: int) -> int:
        return group_number & 0x3F

    def _encode_power_state(self, power_state: GroupPowerState) -> int:
        return power_state.value << 6

    def _encode_control_method(self, control_method: GroupControlMethod) -> int:
        return control_method.value << 7

    def _encode_open_percentage(self, damper_percentage: int) -> int:
        return damper_percentage & 0x7F

    def _encode_set_point(self, set_point: Optional[int]) -> int:
        if set_point:
            return set_point & 0x3F
        return _INVALID_SETPOINT

    def _encode_has_sensor(self, has_sensor: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(has_sensor, offset=7)

    def _encode_supports_turbo(self, supports_turbo: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(supports_turbo, offset=6)

    def _encode_temperature(self, temperature: Optional[float]) -> int:
        if temperature:
            return utils.encode_temperature(temperature)
        return _TEMP_UNAVAILABLE

    def _encode_spill_active(self, spill_active: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(spill_active, offset=4)

    def _encode_low_battery(self, battery_status: SensorBatteryStatus) -> int:
        return battery_status.value << 7


class GroupStatusDecoder(
    comms.MessageDecoder[At4Header, GroupStatusMessage | GroupStatusRequest]
):
    """Decoder for the Group Status Message and Request.

    Handles both the message and the request because they share the same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: At4Header
    ) -> MessageDecodeResult[GroupStatusMessage | GroupStatusRequest]:
        # If there is no data in the message this is a request for group status.
        if header.message_length == 0:
            return comms.MessageDecodeResult(
                message=GroupStatusRequest(),
                remaining=buffer,
            )

        # Otherwise decode status information for each group:
        if (header.message_length % _STRUCT.size) != 0:
            raise comms.DecodeError(
                f"Message length ({header.message_length}) is not "
                f"a multiple of Group Status size ({_STRUCT.size})."
            )

        groups: list[GroupStatusData] = []
        for _ in range(header.message_length // _STRUCT.size):
            (
                b1,
                b2,
                b3,
                encoded_has_sensor,
                b56,
            ) = _STRUCT.unpack_from(buffer)
            has_sensor = self._decode_has_sensor(encoded_has_sensor)
            groups.append(
                GroupStatusData(
                    group_number=self._decode_group_number(b1),
                    power_state=self._decode_power_state(b1),
                    control_method=self._decode_control_method(b2),
                    spill_active=self._decode_spill_active(b56),
                    supports_turbo=self._decode_supports_turbo(b3),
                    has_sensor=has_sensor,
                    battery_status=self._decode_battery_status(b3),
                    temperature=self._decode_temperature(has_sensor, b56),
                    damper_percentage=self._decode_open_percentage(b2),
                    set_point=self._decode_set_point(has_sensor, b3),
                )
            )

            buffer = buffer[_STRUCT.size :]

        return comms.MessageDecodeResult(
            message=GroupStatusMessage(groups), remaining=buffer
        )

    def _decode_group_number(self, byte1: int) -> int:
        return byte1 & 0x3F

    def _decode_power_state(self, byte1: int) -> GroupPowerState:
        return GroupPowerState((byte1 & 0xC0) >> 6)

    def _decode_control_method(self, byte2: int) -> GroupControlMethod:
        return GroupControlMethod((byte2 & 0x80) >> 7)

    def _decode_spill_active(self, byte56: int) -> bool:
        return encoding.bit_to_bool(byte56, offset=4)

    def _decode_supports_turbo(self, byte3: int) -> bool:
        return encoding.bit_to_bool(byte3, offset=6)

    def _decode_has_sensor(self, encoded_has_sensor: int) -> bool:
        return encoding.bit_to_bool(encoded_has_sensor, offset=7)

    def _decode_battery_status(self, byte3: int) -> SensorBatteryStatus:
        return SensorBatteryStatus((byte3 & 0x80) >> 7)

    def _decode_temperature(self, has_sensor: bool, byte56: int) -> Optional[float]:  # noqa: FBT001
        encoded_temperature = byte56 & 0xFFE0
        if not has_sensor or encoded_temperature == _TEMP_UNAVAILABLE:
            return None
        return utils.decode_temperature(encoded_temperature)

    def _decode_open_percentage(self, byte2: int) -> int:
        return byte2 & 0x7F

    def _decode_set_point(self, has_sensor: bool, byte3: int) -> Optional[int]:  # noqa: FBT001
        if has_sensor:
            return byte3 & 0x3F
        return None
