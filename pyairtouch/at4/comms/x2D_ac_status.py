"""Definition of the AC Status Message (0x2D).

AC Status messages report the mode, fan speed, and set-point of ACs in the
AirTouch system. Each message can include status for one or more ACs (in a
multi-AC AirTouch system).

The AC Status message will be sent automatically whenever the AC Status changes.
An AC Status Request can also be sent to request current AC status from the
AirTouch 4.

Since the AC Status Request uses the same message ID as the AC Status Message, a
shared Encoded and Decoder are used.
"""  # noqa: N999

import enum
import struct
from collections.abc import Sequence
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import utils
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.comms import MessageDecodeResult, encoding

MESSAGE_ID = 0x2D


class AcPowerState(enum.Enum):
    """Power states of an air-conditioner."""

    OFF = 0
    ON = 1


class AcMode(enum.Enum):
    """Modes of an air-conditioner."""

    AUTO = 0
    HEAT = 1
    DRY = 2
    FAN = 3
    COOL = 4
    AUTO_HEAT = 8
    AUTO_COOL = 9


class AcFanSpeed(enum.Enum):
    """Fan speeds of an air-conditioner."""

    AUTO = 0
    QUIET = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    POWERFUL = 5
    TURBO = 6


@dataclass
class AcStatusData:
    """Status data for a single air-conditioner."""

    ac_number: int
    power_state: AcPowerState
    mode: AcMode
    fan_speed: AcFanSpeed
    spill_active: bool
    timer_set: bool
    set_point: int
    """Target setpoint in degrees Celsius."""
    temperature: float
    """Current temperature in degrees Celsius."""

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


_STRUCT = struct.Struct("!BBBxHH")


class AcStatusEncoder(
    comms.MessageEncoder[At4Header, AcStatusMessage | AcStatusRequest]
):
    """Encoder for AC Status Messages and Requests.

    A common encoder is used for messages and requests because they share the
    same message ID.
    """

    @override
    def size(self, message: AcStatusMessage | AcStatusRequest) -> int:
        if isinstance(message, AcStatusRequest):
            return 0  # AC Status Request is empty

        return _STRUCT.size * len(message.ac_status)

    @override
    def encode(
        self, header: At4Header, message: AcStatusMessage | AcStatusRequest
    ) -> bytes:
        if isinstance(message, AcStatusRequest):
            return b""

        buffer = bytearray()
        for ac_status in message.ac_status:
            encoded_ac_number = self._encode_ac_number(ac_status.ac_number)
            encoded_power_state = self._encode_power_state(ac_status.power_state)
            encoded_mode = self._encode_mode(ac_status.mode)
            encoded_fan_speed = self._encode_fan_speed(ac_status.fan_speed)
            encoded_spill_active = self._encode_spill_active(ac_status.spill_active)
            encoded_timer_set = self._encode_timer_set(ac_status.timer_set)
            encoded_set_point = self._encode_set_point(ac_status.set_point)
            encoded_temperature = utils.encode_temperature(ac_status.temperature)

            b1 = encoded_power_state + encoded_ac_number
            b2 = encoded_mode + encoded_fan_speed
            b3 = encoded_spill_active + encoded_timer_set + encoded_set_point

            buffer.extend(
                _STRUCT.pack(b1, b2, b3, encoded_temperature, ac_status.error_code)
            )

        return buffer

    def _encode_ac_number(self, ac_number: int) -> int:
        return ac_number & 0x3F

    def _encode_power_state(self, power_state: AcPowerState) -> int:
        return (power_state.value << 6) & 0xC0

    def _encode_mode(self, mode: AcMode) -> int:
        return (mode.value << 4) & 0xF0

    def _encode_fan_speed(self, fan_speed: AcFanSpeed) -> int:
        return fan_speed.value & 0x0F

    def _encode_spill_active(self, spill_active: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(spill_active, 7)

    def _encode_timer_set(self, timer_set: bool) -> int:  # noqa: FBT001
        return encoding.bool_to_bit(timer_set, 6)

    def _encode_set_point(self, set_point: int) -> int:
        return set_point & 0x3F


class AcStatusDecoder(
    comms.MessageDecoder[At4Header, AcStatusMessage | AcStatusRequest]
):
    """Decoder for the AC Status Message and Request.

    A common decoder is used for the message and request since they share the
    same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: At4Header
    ) -> MessageDecodeResult[AcStatusMessage | AcStatusRequest]:
        # If there is no data in the message this is a request for AC status.
        if header.message_length == 0:
            return comms.MessageDecodeResult(
                message=AcStatusRequest(),
                remaining=buffer,
            )

        # Otherwise decode status information for each AC:
        if (header.message_length % _STRUCT.size) != 0:
            raise comms.DecodeError(
                f"Message length ({header.message_length}) is not "
                f"a multiple of AC Status size ({_STRUCT.size})."
            )

        ac_status: list[AcStatusData] = []
        for _ in range(header.message_length // _STRUCT.size):
            (
                b1,
                b2,
                b3,
                encoded_temperature,
                error_code,
            ) = _STRUCT.unpack_from(buffer)

            ac_status.append(
                AcStatusData(
                    ac_number=self._decode_ac_number(b1),
                    power_state=self._decode_power_state(b1),
                    mode=self._decode_mode(b2),
                    fan_speed=self._decode_fan_speed(b2),
                    spill_active=self._decode_spill_active(b3),
                    timer_set=self._decode_timer_set(b3),
                    set_point=self._decode_set_point(b3),
                    temperature=utils.decode_temperature(encoded_temperature),
                    error_code=error_code,
                )
            )

            buffer = buffer[_STRUCT.size :]

        return comms.MessageDecodeResult(
            message=AcStatusMessage(ac_status),
            remaining=buffer,
        )

    def _decode_ac_number(self, byte1: int) -> int:
        return byte1 & 0x3F

    def _decode_power_state(self, byte1: int) -> AcPowerState:
        return AcPowerState((byte1 & 0xC0) >> 6)

    def _decode_mode(self, byte2: int) -> AcMode:
        return AcMode((byte2 & 0xF0) >> 4)

    def _decode_fan_speed(self, byte2: int) -> AcFanSpeed:
        return AcFanSpeed(byte2 & 0x0F)

    def _decode_spill_active(self, byte3: int) -> bool:
        return encoding.bit_to_bool(byte3, 7)

    def _decode_timer_set(self, byte3: int) -> bool:
        return encoding.bit_to_bool(byte3, 6)

    def _decode_set_point(self, byte3: int) -> int:
        return byte3 & 0x3F
