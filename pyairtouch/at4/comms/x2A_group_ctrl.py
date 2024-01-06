"""Definition of the Group Control Message (0x2A).

Group control messages are used to control the power and setpoint/damper state
of zones in the AirTouch system. Each message can control the state of one zone.
"""  # noqa: N999

import enum
import struct
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.comms import MessageDecodeResult

MESSAGE_ID = 0x2A


class GroupPowerControl(enum.Enum):
    """Options for controlling the power state of a group."""

    TOGGLE = 1
    TURN_OFF = 2
    TURN_ON = 3
    TURBO = 5
    UNCHANGED = 0


class GroupControlMethod(enum.Enum):
    """Options for setting the control method of the group."""

    CHANGE = 1
    """Change the control method according to the selected setting."""
    DAMPER = 2
    """Set to damper percentage control."""
    TEMPERATURE = 3
    """Set to temperature set-point control."""
    UNCHANGED = 0


class GroupIncreaseDecrease(enum.Enum):
    """Increase or decrease the current group setting by one unit.

    If the group is currently in temperature control, the set-point will be
    increased/decreased by one degree Celsius.

    If the group is currently in damper control, the current open percentage
    will by increased/decreased by 5%.
    """

    DECREASE = 2
    INCREASE = 3


@dataclass
class GroupDamperControl:
    """Set a specific damper percentage."""

    open_percentage: int


@dataclass
class GroupSetPointControl:
    """Change the group set-point to the specified temperature in degrees Celcius."""

    set_point: int


GroupSetting = GroupIncreaseDecrease | GroupDamperControl | GroupSetPointControl | None


@dataclass
class GroupControlMessage(comms.Message):
    """The Group Control Message."""

    group_number: int
    power: GroupPowerControl
    control_method: GroupControlMethod
    setting: GroupSetting

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BBBx")

# Magic numbers from the interface specification
_KEEP_SETTING = 0x00
_SET_PERCENTAGE = 0x04
_SET_SETPOINT = 0x05
_VALUE_INVALID = 0x00


class GroupControlEncoder(comms.MessageEncoder[At4Header, GroupControlMessage]):
    """Encoder for the Group Control message."""

    @override
    def size(self, _: GroupControlMessage) -> int:
        return _STRUCT.size

    @override
    def encode(self, _: At4Header, message: GroupControlMessage) -> bytes:
        encoded_method = self._encode_control_method(message.control_method)
        encoded_setting, encoded_setting_value = self._encode_setting(message.setting)
        encoded_power = self._encode_power(message.power)
        b2 = encoded_setting + encoded_method + encoded_power
        return _STRUCT.pack(message.group_number, b2, encoded_setting_value)

    def _encode_control_method(self, control_method: GroupControlMethod) -> int:
        return (control_method.value << 3) & 0x18

    def _encode_setting(self, setting: GroupSetting) -> tuple[int, int]:
        encoded_setting = _KEEP_SETTING
        setting_value = _VALUE_INVALID

        match setting:
            case GroupIncreaseDecrease():
                encoded_setting = setting.value
            case GroupDamperControl(open_percentage=open_percentage):
                encoded_setting = _SET_PERCENTAGE
                setting_value = open_percentage
            case GroupSetPointControl(set_point=set_point):
                encoded_setting = _SET_SETPOINT
                setting_value = set_point
        return (encoded_setting << 5, setting_value)

    def _encode_power(self, power: GroupPowerControl) -> int:
        return power.value


class GroupControlDecoder(comms.MessageDecoder[At4Header, GroupControlMessage]):
    """Decoder for the Group Control Message."""

    @override
    def decode(
        self, buffer: bytes | bytearray, header: At4Header
    ) -> MessageDecodeResult[GroupControlMessage]:
        (group_number, b2, setting_value) = _STRUCT.unpack_from(buffer)

        return comms.MessageDecodeResult(
            message=GroupControlMessage(
                group_number=group_number,
                power=self._decode_power(b2),
                control_method=self._decode_control_method(b2),
                setting=self._decode_setting(b2, setting_value),
            ),
            remaining=buffer[_STRUCT.size :],
        )

    def _decode_power(self, byte2: int) -> GroupPowerControl:
        return GroupPowerControl(byte2 & 0x07)

    def _decode_control_method(self, byte2: int) -> GroupControlMethod:
        return GroupControlMethod((byte2 & 0x18) >> 3)

    def _decode_setting(self, byte2: int, setting_value: int) -> GroupSetting:
        setting_type = (byte2 & 0xE0) >> 5

        try:
            return GroupIncreaseDecrease(setting_type)
        except ValueError:
            # This was not an Increase/Decrease control request
            pass

        if setting_type == _SET_SETPOINT:
            return GroupSetPointControl(set_point=setting_value)

        if setting_type == _SET_PERCENTAGE:
            return GroupDamperControl(open_percentage=setting_value)

        # Keep the setting value unchanged.
        return None
