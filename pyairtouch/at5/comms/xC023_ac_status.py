"""Definition of the AC Status Message (0xC023).

AC Status messages report the mode, fan speed, and setpoint of ACs in the
AirTouch system. Each message can include status for one or more ACs (in a
multi-AC AirTouch system).

The AC Status message will be sent automatically whenever the AC Status changes.
An AC Status Request can also be sent to request current AC status from the
AirTouch 5.

Since the AC Status Request uses the same message ID as the AC Status Message, a
shared Encoder and Decoder are used.

This message is a sub-message of the Control Command and Status Message.
"""  # noqa: N999

import enum
import struct
from collections.abc import Sequence
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import utils, xC0_ctrl_status
from pyairtouch.comms import encoding

MESSAGE_ID = 0x23


class AcPowerState(enum.Enum):
    """Current power state of the air-conditioner."""

    OFF = 0
    ON = 1
    OFF_AWAY = 2
    ON_AWAY = 3
    SLEEP = 5


class AcMode(enum.Enum):
    """Current mode of the air-conditioner."""

    AUTO = 0
    HEAT = 1
    DRY = 2
    FAN = 3
    COOL = 4
    AUTO_HEAT = 8
    AUTO_COOL = 9


class AcFanSpeed(enum.Enum):
    """Current fan speed of the air-conditioner."""

    AUTO = 0
    QUIET = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    POWERFUL = 5
    TURBO = 6
    INTELLIGENT_AUTO = 9  # 9 to 14


@dataclass
class AcStatusData:
    """Status data for a single air-conditioner."""

    ac_number: int
    power_state: AcPowerState
    mode: AcMode
    fan_speed: AcFanSpeed
    turbo_active: bool
    bypass_active: bool
    spill_active: bool
    timer_set: bool
    set_point: float
    temperature: float

    error_code: int
    """The error code for this AC.

    See also has_error().
    """

    def has_error(self) -> bool:
        """Whether the AC has an active error."""
        return self.error_code != 0


@dataclass
class AcStatusMessage(comms.Message):
    """The AC Status Message."""

    ac_status: Sequence[AcStatusData]

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class AcStatusRequest(comms.Message):
    """Request for AC Status."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BBBBHHxx")

_BYTE4_UNUSED_BITS = 0b11000000  # From the example messages and as per real messages


class AcStatusEncoder(
    xC0_ctrl_status.ControlStatusSubEncoder[AcStatusMessage | AcStatusRequest]
):
    """Encoder for the AC Status Message and Request.

    Handles both the message and request since they have the same message ID.
    """

    @override
    def non_repeat_size(self, message: AcStatusMessage | AcStatusRequest) -> int:
        # No non-repeating data
        return 0

    @override
    def repeat_count(self, message: AcStatusMessage | AcStatusRequest) -> int:
        if isinstance(message, AcStatusRequest):
            return 0
        return len(message.ac_status)

    @override
    def repeat_size(self, message: AcStatusMessage | AcStatusRequest) -> int:
        if isinstance(message, AcStatusRequest):
            return 0
        return _STRUCT.size

    @override
    def encode(
        self,
        _: xC0_ctrl_status.ControlStatusSubHeader,
        message: AcStatusMessage | AcStatusRequest,
    ) -> bytes:
        if isinstance(message, AcStatusRequest):
            # AcStatusRequest has no content
            return b""

        buffer = bytearray()
        for ac in message.ac_status:
            encoded_ac_number = self._encode_ac_number(ac.ac_number)
            encoded_power_state = self._encode_power_state(ac.power_state)
            encoded_mode = self._encode_mode(ac.mode)
            encoded_fan_speed = self._encode_fan_speed(ac.fan_speed)
            encoded_set_point = utils.encode_set_point(ac.set_point)
            encoded_turbo_active = self._encode_turbo_active(ac.turbo_active)
            encoded_bypass_active = self._encode_bypass_active(ac.bypass_active)
            encoded_spill_active = self._encode_spill_active(ac.spill_active)
            encoded_timer_status = self._encode_timer_status(ac.timer_set)
            encoded_temperature = utils.encode_temperature(ac.temperature)

            b1 = encoded_ac_number + encoded_power_state
            b2 = encoded_mode + encoded_fan_speed
            b4 = (
                _BYTE4_UNUSED_BITS
                + encoded_turbo_active
                + encoded_bypass_active
                + encoded_spill_active
                + encoded_timer_status
            )

            buffer.extend(
                _STRUCT.pack(
                    b1, b2, encoded_set_point, b4, encoded_temperature, ac.error_code
                )
            )

        return buffer

    def _encode_ac_number(self, ac_number: int) -> int:
        return ac_number & 0x0F

    def _encode_power_state(self, power_state: AcPowerState) -> int:
        return (power_state.value << 4) & 0xF0

    def _encode_mode(self, mode: AcMode) -> int:
        return (mode.value << 4) & 0xF0

    def _encode_fan_speed(self, fan_speed: AcFanSpeed) -> int:
        return fan_speed.value & 0x0F

    def _encode_turbo_active(self, turbo_active: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(turbo_active, 3)

    def _encode_bypass_active(self, bypass_active: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(bypass_active, 2)

    def _encode_spill_active(self, spill_active: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(spill_active, 1)

    def _encode_timer_status(self, timer_set: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(timer_set, 0)


class AcStatusDecoder(
    comms.MessageDecoder[
        xC0_ctrl_status.ControlStatusSubHeader, AcStatusMessage | AcStatusRequest
    ]
):
    """Decoder for the AC Status Message and Request."""

    @override
    def decode(
        self, buffer: bytes | bytearray, header: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[AcStatusMessage | AcStatusRequest]:
        # If there is no data, this is a request for AC Status
        if header.repeat_count == 0 and header.repeat_length == 0:
            return comms.MessageDecodeResult(
                message=AcStatusRequest(),
                remaining=buffer,
            )

        # Otherwise decode AC Status information for each AC:
        if header.repeat_length != _STRUCT.size:
            raise comms.DecodeError(
                f"Header repeat_length ({header.repeat_length}) != "
                f"AC Status Data size ({_STRUCT.size})"
            )

        acs: list[AcStatusData] = []
        for _ in range(header.repeat_count):
            (
                b1,
                b2,
                set_point_raw,
                b4,
                temp_raw,
                error_code,
            ) = _STRUCT.unpack_from(buffer)
            acs.append(
                AcStatusData(
                    ac_number=self._decode_ac_number(b1),
                    power_state=self._decode_power_state(b1),
                    mode=self._decode_mode(b2),
                    fan_speed=self._decode_fan_speed(b2),
                    turbo_active=self._decode_turbo(b4),
                    bypass_active=self._decode_bypass(b4),
                    spill_active=self._decode_spill(b4),
                    timer_set=self._decode_timer_status(b4),
                    set_point=utils.decode_set_point(set_point_raw),
                    temperature=utils.decode_temperature(temp_raw),
                    error_code=error_code,
                )
            )
            buffer = buffer[_STRUCT.size :]

        return comms.MessageDecodeResult(
            message=AcStatusMessage(acs),
            remaining=buffer,
        )

    def _decode_ac_number(self, byte1: int) -> int:
        return byte1 & 0x0F

    def _decode_power_state(self, byte1: int) -> AcPowerState:
        return AcPowerState((byte1 & 0xF0) >> 4)

    def _decode_mode(self, byte2: int) -> AcMode:
        return AcMode((byte2 & 0xF0) >> 4)

    def _decode_fan_speed(self, byte2: int) -> AcFanSpeed:
        fan_speed_int = byte2 & 0x0F
        # Values 9 to 14 all translate to Intelligent Auto
        if fan_speed_int in range(0x09, 0x0F):
            return AcFanSpeed.INTELLIGENT_AUTO
        return AcFanSpeed(fan_speed_int)

    def _decode_turbo(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 3)

    def _decode_bypass(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 2)

    def _decode_spill(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 1)

    def _decode_timer_status(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 0)
