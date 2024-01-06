"""Definition of the AC Ability Message (0x1FFF11).

AC Ability messages report the supported abilities of ACs in the AirTouch 5
system. The AC Ability message also provides the mapping from AC numbers to the
corresponding zone numbers.

To request the AC Ability an AC Ability Request must be sent to the AirTouch 5.
Since the AC Ability Request uses the same ID as the AC Ability Message, a
shared Encoder and Decoder are used.

This message is a sub-message of the Extended Message.
"""  # noqa: N999

import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import x1F_ext
from pyairtouch.at5.comms.xC022_ac_ctrl import AcFanSpeedControl, AcModeControl
from pyairtouch.comms import encoding

MESSAGE_ID = 0xFF11


@dataclass
class AcAbility:
    """Encapsulates the abilities of a single air-conditioner."""

    ac_number: int
    ac_name: str
    start_zone: int
    zone_count: int
    ac_mode_support: Mapping[AcModeControl, bool]
    fan_speed_support: Mapping[AcFanSpeedControl, bool]
    min_cool_set_point: int
    max_cool_set_point: int
    min_heat_set_point: int
    max_heat_set_point: int


@dataclass
class AcAbilityMessage(comms.Message):
    """The AC Ability Message."""

    ac_abilities: Sequence[AcAbility]

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class AcAbilityRequest(comms.Message):
    """A request for AC Ability."""

    ac_number: int | Literal["ALL"]
    """Request AC Ability information for a single AC, or all ACs."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BB16sBBBBBBBB")


class AcAbilityEncoder(
    comms.MessageEncoder[
        x1F_ext.ExtendedMessageSubHeader, AcAbilityMessage | AcAbilityRequest
    ]
):
    """Encoder for AC Ability Messages and Requests.

    Handles both the message the the request because they share the same message ID.
    """

    @override
    def size(self, message: AcAbilityMessage | AcAbilityRequest) -> int:
        if isinstance(message, AcAbilityRequest):
            if message.ac_number == "ALL":
                # No content to request information for all ACs
                return 0
            # AC number only
            return 1
        return _STRUCT.size * len(message.ac_abilities)

    @override
    def encode(
        self,
        _: x1F_ext.ExtendedMessageSubHeader,
        message: AcAbilityMessage | AcAbilityRequest,
    ) -> bytes:
        if isinstance(message, AcAbilityRequest):
            if message.ac_number == "ALL":
                # No Content for an "ALL" request
                return b""
            return bytes([message.ac_number])

        buffer = bytearray()
        for ac in message.ac_abilities:
            following_length = 24  # As per communication protocol
            encoded_ac_name = ac.ac_name.encode(encoding=encoding.STRING_ENCODING)
            b23 = self._encode_mode_support(ac.ac_mode_support)
            b24 = self._encode_fan_speed_support(ac.fan_speed_support)

            buffer.extend(
                _STRUCT.pack(
                    ac.ac_number,
                    following_length,
                    encoded_ac_name,
                    ac.start_zone,
                    ac.zone_count,
                    b23,
                    b24,
                    ac.min_cool_set_point,
                    ac.max_cool_set_point,
                    ac.min_heat_set_point,
                    ac.max_heat_set_point,
                )
            )
        return buffer

    def _encode_mode_support(self, mode_support: Mapping[AcModeControl, bool]) -> int:
        return (
            encoding.bool_to_bit(mode_support[AcModeControl.AUTO], 0)
            + encoding.bool_to_bit(mode_support[AcModeControl.HEAT], 1)
            + encoding.bool_to_bit(mode_support[AcModeControl.DRY], 2)
            + encoding.bool_to_bit(mode_support[AcModeControl.FAN], 3)
            + encoding.bool_to_bit(mode_support[AcModeControl.COOL], 4)
        )

    def _encode_fan_speed_support(
        self, fan_speed_support: Mapping[AcFanSpeedControl, bool]
    ) -> int:
        return (
            encoding.bool_to_bit(fan_speed_support[AcFanSpeedControl.AUTO], 0)
            + encoding.bool_to_bit(fan_speed_support[AcFanSpeedControl.QUIET], 1)
            + encoding.bool_to_bit(fan_speed_support[AcFanSpeedControl.LOW], 2)
            + encoding.bool_to_bit(fan_speed_support[AcFanSpeedControl.MEDIUM], 3)
            + encoding.bool_to_bit(fan_speed_support[AcFanSpeedControl.HIGH], 4)
            + encoding.bool_to_bit(fan_speed_support[AcFanSpeedControl.POWERFUL], 5)
            + encoding.bool_to_bit(fan_speed_support[AcFanSpeedControl.TURBO], 6)
            + encoding.bool_to_bit(
                fan_speed_support[AcFanSpeedControl.INTELLIGENT_AUTO], 7
            )
        )


class AcAbilityDecoder(
    comms.MessageDecoder[
        x1F_ext.ExtendedMessageSubHeader, AcAbilityMessage | AcAbilityRequest
    ]
):
    """Decoder for the AC Ability Message and Request.

    Handles both the message and the request because they share a message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: x1F_ext.ExtendedMessageSubHeader
    ) -> comms.MessageDecodeResult[AcAbilityMessage | AcAbilityRequest]:
        # If there is no data, this is a request for all ACs
        if header.message_length == 0:
            return comms.MessageDecodeResult(
                message=AcAbilityRequest(ac_number="ALL"),
                remaining=buffer,
            )

        # If there is only one byte, then this is a request for a specific AC
        if header.message_length == 1:
            return comms.MessageDecodeResult(
                message=AcAbilityRequest(ac_number=buffer[0]),
                remaining=buffer[1:],
            )

        # Otherwise decode ability information for one or more ACs:
        if header.message_length % _STRUCT.size != 0:
            raise comms.DecodeError(
                f"Data length ({header.message_length}) is not a multiple of "
                f"AC Ability information length ({_STRUCT.size})"
            )

        ac_abilities: list[AcAbility] = []
        for _ in range(header.message_length // _STRUCT.size):
            (
                ac_number,
                _,  # Following length
                ac_name_raw,
                start_zone,
                zone_count,
                b23,
                b24,
                min_cool_set_point,
                max_cool_set_point,
                min_heat_set_point,
                max_heat_set_point,
            ) = _STRUCT.unpack_from(buffer)
            buffer = buffer[_STRUCT.size :]

            ac_abilities.append(
                AcAbility(
                    ac_number=ac_number,
                    ac_name=encoding.decode_c_string(ac_name_raw),
                    start_zone=start_zone,
                    zone_count=zone_count,
                    ac_mode_support=self._decode_ac_mode_support(b23),
                    fan_speed_support=self._decode_fan_speed_support(b24),
                    min_cool_set_point=min_cool_set_point,
                    max_cool_set_point=max_cool_set_point,
                    min_heat_set_point=min_heat_set_point,
                    max_heat_set_point=max_heat_set_point,
                )
            )

        return comms.MessageDecodeResult(
            message=AcAbilityMessage(ac_abilities=ac_abilities),
            remaining=buffer,
        )

    def _decode_ac_mode_support(self, byte23: int) -> Mapping[AcModeControl, bool]:
        return {
            AcModeControl.AUTO: encoding.bit_to_bool(byte23, 0),
            AcModeControl.HEAT: encoding.bit_to_bool(byte23, 1),
            AcModeControl.DRY: encoding.bit_to_bool(byte23, 2),
            AcModeControl.FAN: encoding.bit_to_bool(byte23, 3),
            AcModeControl.COOL: encoding.bit_to_bool(byte23, 4),
            AcModeControl.UNCHANGED: True,  # Always supported
        }

    def _decode_fan_speed_support(
        self, byte24: int
    ) -> Mapping[AcFanSpeedControl, bool]:
        return {
            AcFanSpeedControl.AUTO: encoding.bit_to_bool(byte24, 0),
            AcFanSpeedControl.QUIET: encoding.bit_to_bool(byte24, 1),
            AcFanSpeedControl.LOW: encoding.bit_to_bool(byte24, 2),
            AcFanSpeedControl.MEDIUM: encoding.bit_to_bool(byte24, 3),
            AcFanSpeedControl.HIGH: encoding.bit_to_bool(byte24, 4),
            AcFanSpeedControl.POWERFUL: encoding.bit_to_bool(byte24, 5),
            AcFanSpeedControl.TURBO: encoding.bit_to_bool(byte24, 6),
            AcFanSpeedControl.INTELLIGENT_AUTO: encoding.bit_to_bool(byte24, 7),
            AcFanSpeedControl.UNCHANGED: True,  # Always supported
        }
