"""Definition of the AC Control Message (0x2C).

AC Control messages are used to control the mode, fan speed, and set-point of
ACs in the AirTouch system. Each message can control the state of a single AC.
"""  # noqa: N999

import enum
import struct
from dataclasses import dataclass
from typing import Any

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.comms import MessageDecodeResult

MESSAGE_ID = 0x2C


class AcPowerControl(enum.Enum):
    """Options for setting the power state of the air-conditioner."""

    TOGGLE = 1
    TURN_OFF = 2
    TURN_ON = 3
    UNCHANGED = 0


class AcModeControl(enum.Enum):
    """Options for setting the mode of the air-conditioner."""

    AUTO = 0
    HEAT = 1
    DRY = 2
    FAN = 3
    COOL = 4
    UNCHANGED = 0xFF

    @classmethod
    def _missing_(cls, _: Any) -> "AcModeControl":  # noqa: ANN401
        # All "other" values are equivalent to no change
        return AcModeControl.UNCHANGED


class AcFanSpeedControl(enum.Enum):
    """Options for setting the fan speed of the air-conditioner."""

    AUTO = 0
    QUIET = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    POWERFUL = 5
    TURBO = 6
    UNCHANGED = 0xFF

    @classmethod
    def _missing_(cls, _: Any) -> "AcFanSpeedControl":  # noqa: ANN401
        # All "other" values are equivalent to no change
        return AcFanSpeedControl.UNCHANGED


class AcIncreaseDecrease(enum.Enum):
    """Increase or decrease the current set-point value by one degree Celsius."""

    INCREASE = 3
    DECREASE = 2


@dataclass
class AcSetPointValue:
    """Change the set-point to a specific value."""

    set_point: int


AcSetPointControl = AcIncreaseDecrease | AcSetPointValue | None


@dataclass
class AcControlMessage(comms.Message):
    """The AC Control Message."""

    ac_number: int
    power: AcPowerControl
    mode: AcModeControl
    fan_speed: AcFanSpeedControl
    set_point_control: AcSetPointControl

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BBBx")

# Magic numbers from the interface specification.
_SET_POINT_CONTROL_UNCHANGED = 0x00
_SET_POINT_CONTROL_VALUE = 0x01
_SET_POINT_INVALID = 0x00  # Based on the example messages


class AcControlEncoder(comms.MessageEncoder[At4Header, AcControlMessage]):
    """Encoder for the AC Control Message."""

    @override
    def size(self, _: AcControlMessage) -> int:
        return _STRUCT.size

    @override
    def encode(self, header: At4Header, message: AcControlMessage) -> bytes:
        encoded_ac_number = self._encode_ac_number(message.ac_number)
        encoded_power = self._encode_power(message.power)
        encoded_mode = self._encode_mode(message.mode)
        encoded_fan_speed = self._encode_fan_speed(message.fan_speed)
        encoded_set_point_control = self._encode_set_point_control(
            message.set_point_control
        )

        b1 = encoded_power + encoded_ac_number
        b2 = encoded_mode + encoded_fan_speed
        return _STRUCT.pack(b1, b2, encoded_set_point_control)

    def _encode_ac_number(self, ac_number: int) -> int:
        return ac_number & 0x3F

    def _encode_power(self, power: AcPowerControl) -> int:
        return (power.value << 6) & 0xC0

    def _encode_mode(self, mode: AcModeControl) -> int:
        return (mode.value << 4) & 0xF0

    def _encode_fan_speed(self, fan_speed: AcFanSpeedControl) -> int:
        return fan_speed.value & 0x0F

    def _encode_set_point_control(self, set_point_control: AcSetPointControl) -> int:
        control_type = _SET_POINT_CONTROL_UNCHANGED
        value = _SET_POINT_INVALID
        match set_point_control:
            case AcIncreaseDecrease():
                control_type = set_point_control.value
            case AcSetPointValue(set_point=set_point):
                control_type = _SET_POINT_CONTROL_VALUE
                value = set_point

        encoded_control_type = (control_type << 6) & 0xC0
        encoded_value = value & 0x3F
        return encoded_control_type + encoded_value


class AcControlDecoder(comms.MessageDecoder[At4Header, AcControlMessage]):
    """Decoder for the AC Control Message."""

    @override
    def decode(
        self, buffer: bytes | bytearray, _: At4Header
    ) -> MessageDecodeResult[AcControlMessage]:
        (b1, b2, encoded_set_point_control) = _STRUCT.unpack_from(buffer)
        return comms.MessageDecodeResult(
            message=AcControlMessage(
                ac_number=self._decode_ac_number(b1),
                power=self._decode_power(b1),
                mode=self._decode_mode(b2),
                fan_speed=self._decode_fan_speed(b2),
                set_point_control=self._decode_set_point_control(
                    encoded_set_point_control
                ),
            ),
            remaining=buffer[_STRUCT.size :],
        )

    def _decode_ac_number(self, byte1: int) -> int:
        return byte1 & 0x3F

    def _decode_power(self, byte1: int) -> AcPowerControl:
        return AcPowerControl((byte1 & 0xC0) >> 6)

    def _decode_mode(self, byte2: int) -> AcModeControl:
        return AcModeControl((byte2 & 0xF0) >> 4)

    def _decode_fan_speed(self, byte2: int) -> AcFanSpeedControl:
        return AcFanSpeedControl(byte2 & 0x0F)

    def _decode_set_point_control(
        self, encoded_set_point_control: int
    ) -> AcSetPointControl:
        control_type = (encoded_set_point_control & 0xC0) >> 6
        value = encoded_set_point_control & 0x3F

        try:
            return AcIncreaseDecrease(control_type)
        except ValueError:
            # Not an increase/decrease command
            pass

        if control_type == _SET_POINT_CONTROL_VALUE:
            return AcSetPointValue(set_point=value)

        return None
