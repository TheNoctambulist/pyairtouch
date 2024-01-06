"""Definition of the AC Control Message (0xC022).

AC Control messages are used to control the mode, fan speed, and setpoint of ACs
in the AirTouch system. Each message can control one or more ACs (in a multi-AC
AirTouch system).

This message is a sub-message of the Control Command and Status Message.
"""  # noqa: N999

import enum
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import utils, xC0_ctrl_status

MESSAGE_ID = 0x22


class AcPowerControl(enum.Enum):
    """Options for controlling the power state of the air-conditioner."""

    TOGGLE = 1
    TURN_OFF = 2
    TURN_ON = 3
    SET_TO_AWAY = 4
    SET_TO_SLEEP = 5
    UNCHANGED = 0  # Zero as per the example messages

    @classmethod
    def _missing_(cls, _: Any) -> "AcPowerControl":  # noqa: ANN401
        # All "other" values are equivalent to no change
        return AcPowerControl.UNCHANGED


class AcModeControl(enum.Enum):
    """Options for controlling the mode of the air-conditioner."""

    AUTO = 0
    HEAT = 1
    DRY = 2
    FAN = 3
    COOL = 4
    UNCHANGED = 0xFF  # 'F' as per the example messages

    @classmethod
    def _missing_(cls, _: Any) -> "AcModeControl":  # noqa: ANN401
        # All "other" values are equivalent to no change
        return AcModeControl.UNCHANGED


class AcFanSpeedControl(enum.Enum):
    """Options for controlling the fan speed of the air-conditioner."""

    AUTO = 0
    QUIET = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    POWERFUL = 5
    TURBO = 6
    INTELLIGENT_AUTO = 8
    UNCHANGED = 0xFF

    @classmethod
    def _missing_(cls, _: Any) -> "AcFanSpeedControl":  # noqa: ANN401
        # All "other" values are equivalent to no change
        return AcFanSpeedControl.UNCHANGED


@dataclass
class AcControlData:
    """Control data for a single air-conditioner."""

    ac_number: int
    power: AcPowerControl
    mode: AcModeControl
    fan_speed: AcFanSpeedControl
    set_point: Optional[float]


@dataclass
class AcControlMessage(comms.Message):
    """The AC Control Message."""

    ac_control: Sequence[AcControlData]

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BBBB")

# Magic numbers from the interface specification
_SET_POINT_UNCHANGED = 0x00
_SET_POINT_CHANGE = 0x40


class AcControlEncoder(xC0_ctrl_status.ControlStatusSubEncoder[AcControlMessage]):
    """Encoder for the AC Control Message."""

    @override
    def non_repeat_size(self, message: AcControlMessage) -> int:
        # No non-repeating data
        return 0

    @override
    def repeat_count(self, message: AcControlMessage) -> int:
        return len(message.ac_control)

    @override
    def repeat_size(self, message: AcControlMessage) -> int:
        return _STRUCT.size

    @override
    def encode(
        self, _: xC0_ctrl_status.ControlStatusSubHeader, message: AcControlMessage
    ) -> bytes:
        buffer = bytearray()
        for control in message.ac_control:
            encoded_ac_number = self._encode_ac_number(control.ac_number)
            encoded_power = self._encode_power(control.power)
            encoded_mode = self._encode_mode(control.mode)
            encoded_fan_speed = self._encode_fan_speed(control.fan_speed)
            encoded_set_point_control, encoded_set_point = self._encode_set_point(
                control.set_point
            )

            b1 = encoded_ac_number + encoded_power
            b2 = encoded_mode + encoded_fan_speed

            buffer.extend(
                _STRUCT.pack(b1, b2, encoded_set_point_control, encoded_set_point)
            )
        return buffer

    def _encode_ac_number(self, ac_number: int) -> int:
        return ac_number & 0x0F

    def _encode_power(self, power: AcPowerControl) -> int:
        return (power.value << 4) & 0xF0

    def _encode_mode(self, mode: AcModeControl) -> int:
        return (mode.value << 4) & 0xF0

    def _encode_fan_speed(self, fan_speed: AcFanSpeedControl) -> int:
        return fan_speed.value & 0x0F

    def _encode_set_point(self, set_point: Optional[float]) -> tuple[int, int]:
        if set_point:
            return _SET_POINT_CHANGE, utils.encode_set_point(set_point)
        # Uses 0xFF as the unchanged value based on the examples in the protocol
        # specficiation.
        return _SET_POINT_UNCHANGED, 0xFF


class AcControlDecoder(
    comms.MessageDecoder[xC0_ctrl_status.ControlStatusSubHeader, AcControlMessage]
):
    """Decoder for the AC Control Message."""

    @override
    def decode(
        self, buffer: bytes | bytearray, header: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[AcControlMessage]:
        ac_control: list[AcControlData] = []
        for _ in range(header.repeat_count):
            (b1, b2, set_point_control, set_point_raw) = _STRUCT.unpack_from(buffer)
            ac_control.append(
                AcControlData(
                    ac_number=self._decode_ac_number(b1),
                    power=self._decode_power(b1),
                    mode=self._decode_mode(b2),
                    fan_speed=self._decode_fan_speed(b2),
                    set_point=self._decode_set_point(set_point_control, set_point_raw),
                )
            )
            buffer = buffer[_STRUCT.size :]

        return comms.MessageDecodeResult(
            message=AcControlMessage(ac_control=ac_control),
            remaining=buffer,
        )

    def _decode_ac_number(self, byte1: int) -> int:
        return byte1 & 0x0F

    def _decode_power(self, byte1: int) -> AcPowerControl:
        value = (byte1 & 0xF0) >> 4
        return AcPowerControl(value)

    def _decode_mode(self, byte2: int) -> AcModeControl:
        value = (byte2 & 0xF0) >> 4
        return AcModeControl(value)

    def _decode_fan_speed(self, byte2: int) -> AcFanSpeedControl:
        value = byte2 & 0x0F
        return AcFanSpeedControl(value)

    def _decode_set_point(
        self, set_point_control: int, set_point_raw: int
    ) -> Optional[float]:
        if set_point_control == _SET_POINT_UNCHANGED:
            return None
        if set_point_control == _SET_POINT_CHANGE:
            return utils.decode_set_point(set_point_raw)

        raise comms.DecodeError(f"Invalid set_point_control value: {set_point_control}")
