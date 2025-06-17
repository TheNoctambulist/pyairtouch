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
import logging
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import utils, xC0_ctrl_status
from pyairtouch.comms import encoding, log

MESSAGE_ID = 0x23

_LOGGER = logging.getLogger(__name__)


class AcPowerState(enum.Enum):
    """Current power state of the air-conditioner.

    OFF_FORCED indicates that the AirTouch system is turned on but the AC itself
    has been turned off by smart control features. This is not yet documented in
    the communication protocol.
    """

    OFF = 0
    ON = 1
    OFF_AWAY = 2
    ON_AWAY = 3
    OFF_FORCED = 4
    SLEEP = 5
    UNKNOWN = 15

    @classmethod
    def _missing_(cls, _: Any) -> "AcPowerState":  # noqa: ANN401
        # The protocol reserves all other values for future use.
        return AcPowerState.UNKNOWN


class AcMode(enum.Enum):
    """Current mode of the air-conditioner."""

    AUTO = 0
    HEAT = 1
    DRY = 2
    FAN = 3
    COOL = 4
    AUTO_HEAT = 8
    AUTO_COOL = 9
    UNKNOWN = 15

    @classmethod
    def _missing_(cls, _: Any) -> "AcMode":  # noqa: ANN401
        # The protocol reserves all other values for future use.
        return AcMode.UNKNOWN


class AcFanSpeed(enum.Enum):
    """Current fan speed of the air-conditioner."""

    AUTO = 0
    QUIET = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    POWERFUL = 5
    TURBO = 6
    INTELLIGENT_AUTO_QUIET = 9
    INTELLIGENT_AUTO_LOW = 10
    INTELLIGENT_AUTO_MEDIUM = 11
    INTELLIGENT_AUTO_HIGH = 12
    INTELLIGENT_AUTO_POWERFUL = 13
    INTELLIGENT_AUTO_TURBO = 14
    UNKNOWN = 15

    @classmethod
    def _missing_(cls, _: Any) -> "AcFanSpeed":  # noqa: ANN401
        # The protocol reserves all other values for future use.
        return AcFanSpeed.UNKNOWN


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


_STRUCT = struct.Struct("!BBBBHH")

# Some versions of the interface don't include padding bytes, so it is not
# included in _STRUCT for parsing.
_PADDING_BYTES = b"\x00\x00"
_PADDING_BYTES_SIZE = len(_PADDING_BYTES)

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
        return _STRUCT.size + _PADDING_BYTES_SIZE

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
            encoded_temperature = self._encode_temperature(ac.temperature)

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
            buffer.extend(_PADDING_BYTES)

        return bytes(buffer)

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

    def _encode_temperature(self, temperature: float) -> int:
        return utils.encode_temperature(temperature) & 0x07FF


class AcStatusDecoder(
    comms.MessageDecoder[
        xC0_ctrl_status.ControlStatusSubHeader, AcStatusMessage | AcStatusRequest
    ]
):
    """Decoder for the AC Status Message and Request."""

    def __init__(self) -> None:
        """Initialise the AcStatusDecoder."""
        # Avoid repeated logging of message length mismatches if the console has
        # an upgraded protocol.
        self._length_mismatch_event = log.LogEvent(_LOGGER, logging.INFO)

        # Log warnings if the protocol has upgraded in a way that impacts the
        # usability of the API
        self._unknown_power_state_event = log.LogEvent(_LOGGER, logging.WARNING)
        self._unknown_mode_event = log.LogEvent(_LOGGER, logging.WARNING)
        self._unknown_fan_speed_event = log.LogEvent(_LOGGER, logging.WARNING)

    @override
    def decode(
        self, buffer: bytes | bytearray, header: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[AcStatusMessage | AcStatusRequest]:
        # If there is no data, this is a request for AC Status
        if header.repeat_count == 0 and header.repeat_length == 0:
            return comms.MessageDecodeResult(
                message=AcStatusRequest(), remaining=bytes(buffer)
            )

        # Otherwise decode AC Status information for each AC:
        if header.repeat_length < _STRUCT.size:
            raise comms.DecodeError(
                f"Header repeat length ({header.repeat_length} < "
                f"AC Status Data size ({_STRUCT.size}))"
            )

        if header.repeat_length not in (
            _STRUCT.size,
            _STRUCT.size + _PADDING_BYTES_SIZE,
        ):
            self._length_mismatch_event.log(
                "Header repeat_length (%d) != AC Status Data size (%d). "
                "Ignoring extra bytes",
                header.repeat_length,
                _STRUCT.size + _PADDING_BYTES_SIZE,
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
                    temperature=self._decode_temperature(temp_raw),
                    error_code=error_code,
                )
            )
            # Progress by the repeat length which will just skip over any unknown bytes.
            buffer = buffer[header.repeat_length :]

        return comms.MessageDecodeResult(
            message=AcStatusMessage(acs), remaining=bytes(buffer)
        )

    def _decode_ac_number(self, byte1: int) -> int:
        return byte1 & 0x0F

    def _decode_power_state(self, byte1: int) -> AcPowerState:
        raw_value = (byte1 & 0xF0) >> 4
        power_state = AcPowerState(raw_value)

        if power_state == AcPowerState.UNKNOWN:
            self._unknown_power_state_event.log(
                "Unknown power state (%d) in AC Status Message", raw_value
            )
        else:
            self._unknown_power_state_event.withdraw()

        return power_state

    def _decode_mode(self, byte2: int) -> AcMode:
        raw_value = (byte2 & 0xF0) >> 4
        mode = AcMode(raw_value)

        if mode == AcMode.UNKNOWN:
            self._unknown_mode_event.log(
                "Unknown mode (%d) in AC Status Message", raw_value
            )
        else:
            self._unknown_mode_event.withdraw()

        return mode

    def _decode_fan_speed(self, byte2: int) -> AcFanSpeed:
        raw_value = byte2 & 0x0F
        fan_speed = AcFanSpeed(raw_value)

        if fan_speed == AcFanSpeed.UNKNOWN:
            self._unknown_fan_speed_event.log(
                "Unknown fan speed (%d) in AC Status Message", raw_value
            )
        else:
            self._unknown_fan_speed_event.withdraw()

        return fan_speed

    def _decode_turbo(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 3)

    def _decode_bypass(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 2)

    def _decode_spill(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 1)

    def _decode_timer_status(self, byte4: int) -> bool:
        return encoding.bit_to_bool(byte4, 0)

    def _decode_temperature(self, temp_raw: int) -> float:
        return utils.decode_temperature(temp_raw & 0x07FF)
