"""Definition of the Zone Control Message (0xC020).

Zone Control messages are used to control the power and setpoint/damper of zones
in the AirTouch system. Each message can control one or more zones.

This message is a sub-message of the Control Command and Status Message.
"""  # noqa: N999

import dataclasses
import enum
import struct
from collections.abc import Sequence
from typing import Any

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import utils, xC0_ctrl_status

MESSAGE_ID = 0x20


class ZonePowerControl(enum.Enum):
    """Options for controlling the power state of a Zone."""

    TOGGLE = 1
    TURN_OFF = 2
    TURN_ON = 3
    TURBO = 5
    UNCHANGED = 0

    @classmethod
    def _missing_(cls, _: Any) -> "ZonePowerControl":  # noqa: ANN401
        return ZonePowerControl.UNCHANGED


class ZoneIncreaseDecrease(enum.Enum):
    """Increase or decrease the current zone setting by one unit.

    If the zone is currently in temperature control, the set-point will be
    increased/decreased by one degree celsius.

    If the zone is currently in damper control, the current open percentage
    will by increased/decreased by 5%.
    """

    DECREASE = 2
    INCREASE = 3


@dataclasses.dataclass
class ZoneDamperControl:
    """Set a specific damper percentage."""

    open_percentage: int


@dataclasses.dataclass
class ZoneSetPointControl:
    """Change the zone set-point to the specified temperature in degrees celsius."""

    set_point: float


ZoneSetting = ZoneIncreaseDecrease | ZoneDamperControl | ZoneSetPointControl | None


@dataclasses.dataclass
class ZoneControlData:
    """Control settings for a single zone."""

    zone_number: int
    zone_power: ZonePowerControl
    zone_setting: ZoneSetting


@dataclasses.dataclass
class ZoneControlMessage(comms.Message):
    """The Zone Control Message."""

    zone_control: Sequence[ZoneControlData]

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_ZONE_CONTROL_STRUCT = struct.Struct("!BBBx")

# Magic numbers from the interface specification
_ZONE_CONTROL_UNCHANGED = 0x00
_ZONE_CONTROL_SET_PERCENTAGE = 0x04
_ZONE_CONTROL_SET_SETPOINT = 0x05
_ZONE_CONTROL_SETTING_VALUE_UNCHANGED = 0xFF  # Based on the example


class ZoneControlEncoder(xC0_ctrl_status.ControlStatusSubEncoder[ZoneControlMessage]):
    """Encoder for Zone Control Messages."""

    @override
    def non_repeat_size(self, msg: ZoneControlMessage) -> int:
        return 0  # No non-repeating data

    @override
    def repeat_count(self, msg: ZoneControlMessage) -> int:
        return len(msg.zone_control)

    @override
    def repeat_size(self, msg: ZoneControlMessage) -> int:
        return _ZONE_CONTROL_STRUCT.size

    @override
    def encode(
        self, _: xC0_ctrl_status.ControlStatusSubHeader, msg: ZoneControlMessage
    ) -> bytes:
        buffer = bytearray()
        for zone in msg.zone_control:
            encoded_power = self._encode_zone_power(zone.zone_power)
            encoded_setting, setting_value = self._encode_zone_setting(
                zone.zone_setting
            )
            b2 = encoded_setting + encoded_power
            buffer.extend(
                _ZONE_CONTROL_STRUCT.pack(zone.zone_number, b2, setting_value)
            )

        return buffer

    def _encode_zone_power(self, zone_power: ZonePowerControl) -> int:
        return zone_power.value

    def _encode_zone_setting(self, zone_setting: ZoneSetting) -> tuple[int, int]:
        encoded_zone_setting = _ZONE_CONTROL_UNCHANGED
        setting_value = _ZONE_CONTROL_SETTING_VALUE_UNCHANGED
        match zone_setting:
            case ZoneIncreaseDecrease():
                encoded_zone_setting = zone_setting.value
            case ZoneDamperControl(open_percentage=open_percentage):
                encoded_zone_setting = _ZONE_CONTROL_SET_PERCENTAGE
                setting_value = open_percentage
            case ZoneSetPointControl(set_point=set_point):
                encoded_zone_setting = _ZONE_CONTROL_SET_SETPOINT
                setting_value = utils.encode_set_point(set_point)

        return (encoded_zone_setting << 5, setting_value)


class ZoneControlDecoder(
    comms.MessageDecoder[xC0_ctrl_status.ControlStatusSubHeader, ZoneControlMessage]
):
    """Decoder for Zone Control Messages."""

    @override
    def decode(
        self, buffer: bytes | bytearray, hdr: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[ZoneControlMessage]:
        zone_control: list[ZoneControlData] = []
        for _ in range(hdr.repeat_count):
            (
                zone_number,
                b2,
                setting_raw,
            ) = _ZONE_CONTROL_STRUCT.unpack_from(buffer)
            buffer = buffer[_ZONE_CONTROL_STRUCT.size :]

            zone_control.append(
                ZoneControlData(
                    zone_number=zone_number,
                    zone_power=self._decode_zone_power(b2),
                    zone_setting=self._decode_zone_setting(b2, setting_raw),
                )
            )

        return comms.MessageDecodeResult(
            message=ZoneControlMessage(zone_control),
            remaining=buffer,
        )

    def _decode_zone_power(self, byte2: int) -> ZonePowerControl:
        return ZonePowerControl(byte2 & 0x07)

    def _decode_zone_setting(self, byte2: int, setting_raw: int) -> ZoneSetting:
        control_type = (byte2 & 0xE0) >> 5

        try:
            return ZoneIncreaseDecrease(control_type)
        except ValueError:
            # This was not an Increase/Decrease control request
            pass

        if control_type == _ZONE_CONTROL_SET_SETPOINT:
            return ZoneSetPointControl(set_point=utils.decode_set_point(setting_raw))

        if control_type == _ZONE_CONTROL_SET_PERCENTAGE:
            return ZoneDamperControl(open_percentage=setting_raw)

        # No zone setting was selected
        return None
