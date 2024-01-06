"""Definition of the AC Ability Message (0x1FFF11).

AC Ability messages report the supported abilities of ACs in the AirTouch 4
system. The AC Ability also provides the mapping from AC numbers to the
corresponding Group numbers.

To request the AC Ability and AC Ability Request must be sent to the AirTouch 5.
Since the AC Ability Request uses the same ID as the AC Ability Message, a
shared encoder and decoder are used.

This message is a sub-message of the Extended Message.
"""  # noqa: N999

import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x1F_ext import ExtendedMessageSubHeader
from pyairtouch.at4.comms.x2C_ac_ctrl import AcFanSpeedControl, AcModeControl
from pyairtouch.comms import MessageDecodeResult, encoding

MESSAGE_ID = 0xFF11


@dataclass
class AcAbility:
    """Encapsulates the abilities of a single air-conditioner."""

    ac_number: int
    ac_name: str
    start_group: int
    group_count: int
    """If there is only one AC, the start_group and group_count are invalid.

    If there is only one AC, all groups belong to that single AC.
    """
    ac_mode_support: Mapping[AcModeControl, bool]
    fan_speed_support: Mapping[AcFanSpeedControl, bool]
    min_set_point: int
    max_set_point: int


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
    """A request for AC Ability information."""

    ac_number: int | Literal["ALL"]
    """Request AC Ability information for a single AC, or all ACs."""

    @override
    @property
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!BB16sBBBBBB")


class AcAbilityEncoder(
    comms.MessageEncoder[
        x1F_ext.ExtendedMessageSubHeader, AcAbilityMessage | AcAbilityRequest
    ]
):
    """Encoder for the AC Ability Message and Request.

    Handles both the message and the request because the share the same message ID.
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
        header: ExtendedMessageSubHeader,
        message: AcAbilityMessage | AcAbilityRequest,
    ) -> bytes:
        if isinstance(message, AcAbilityRequest):
            if message.ac_number == "ALL":
                # No content for an "ALL" request
                return b""
            return bytes([message.ac_number])

        buffer = bytearray()
        for ac in message.ac_abilities:
            following_length = 22  # As per interface specification.
            encoded_ac_name = ac.ac_name.encode(encoding=encoding.STRING_ENCODING)
            b23 = self._encode_mode_support(ac.ac_mode_support)
            b24 = self._encode_fan_speed_support(ac.fan_speed_support)

            buffer.extend(
                _STRUCT.pack(
                    ac.ac_number,
                    following_length,
                    encoded_ac_name,
                    ac.start_group,
                    ac.group_count,
                    b23,
                    b24,
                    ac.min_set_point,
                    ac.max_set_point,
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
        )


class AcAbilityDecoder(
    comms.MessageDecoder[
        x1F_ext.ExtendedMessageSubHeader, AcAbilityMessage | AcAbilityRequest
    ]
):
    """Decoder for AC Ability Message and Request.

    Handles both the message and the request because they share the same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: ExtendedMessageSubHeader
    ) -> MessageDecodeResult[AcAbilityMessage | AcAbilityRequest]:
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

        ac_abilities: list[AcAbility] = []
        offset = 0
        while (offset + _STRUCT.size) <= header.message_length:
            (
                ac_number,
                following_length,
                ac_name_raw,
                start_group,
                group_count,
                b23,
                b24,
                min_set_point,
                max_set_point,
            ) = _STRUCT.unpack_from(buffer, offset=offset)

            # Newer versions of the AirTouch 4 seem to send more bytes, so use the
            # following_length to work out the offset for the next AC. Two bytes
            # are added to account for the AC number and the following length
            # field itself.
            offset += 2 + following_length

            ac_abilities.append(
                AcAbility(
                    ac_number=ac_number,
                    ac_name=encoding.decode_c_string(ac_name_raw),
                    start_group=start_group,
                    group_count=group_count,
                    ac_mode_support=self._decode_ac_mode_support(b23),
                    fan_speed_support=self._decode_fan_speed_support(b24),
                    min_set_point=min_set_point,
                    max_set_point=max_set_point,
                )
            )

        if offset != header.message_length:
            raise comms.DecodeError(
                f"AC Ability only decoded {offset} bytes out of {header.message_length}"
            )

        return comms.MessageDecodeResult(
            message=AcAbilityMessage(ac_abilities),
            remaining=buffer[offset:],
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
            AcFanSpeedControl.UNCHANGED: True,  # Always supported
        }
