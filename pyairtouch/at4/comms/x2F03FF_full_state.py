"""Definition of the Full State Message (0x2F03FF).

The Full State message provides the ID and status of all ACs and groups in the AirTouch
system.

The contents of this message have been reverse engineered.
Currently only a small subset of fields in the full state are implemented since the
primary purpose is to obtain the Airtouch ID in situations when discovery isn't
available.
"""  # noqa: N999

import struct
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.comms import MessageDecodeResult

MESSAGE_ID = 0x03FF


@dataclass
class FullStateMessage(x1F_ext.ExtendedSubMessage2F):
    """The Full State Message."""

    airtouch_id: str
    hardware_version: str
    main_module_version: str

    @property
    @override
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class FullStateRequest(x1F_ext.ExtendedSubMessage2F):
    """Request for full state."""

    @property
    @override
    def message_id(self) -> int:
        return MESSAGE_ID


_STRUCT = struct.Struct("!LHH52x")  # Most bytes not implemented and just made spare
_AC_CONFIG_STRUCT = struct.Struct("!18x")  # Not implemented yet
_GROUP_NAME_STRUCT = struct.Struct("!8s")
_UNKNOWN_STRUCT = struct.Struct("!62x")  # Not implemented yet
_AC_STATE_STRUCT = struct.Struct("!8x")  # Not implemented yet
_GROUP_STATE_STRUCT = struct.Struct("!6x")  # Not implemented yet

_AC_REPEAT_COUNT = 4
_GROUP_REPEAT_COUNT = 16

_VERSION_CHARACTERS = 4
_MAX_AIRTOUCH_ID_CHARACTERS = 8


_FULL_STATE_MESSAGE_LENGTH = (
    _STRUCT.size
    + (_AC_REPEAT_COUNT * _AC_CONFIG_STRUCT.size)
    + (_GROUP_REPEAT_COUNT * _GROUP_NAME_STRUCT.size)
    + _UNKNOWN_STRUCT.size
    + (_AC_REPEAT_COUNT * _AC_STATE_STRUCT.size)
    + (_GROUP_REPEAT_COUNT * _GROUP_STATE_STRUCT.size)
)


class FullStateEncoder(
    comms.MessageEncoder[
        x1F_ext.ExtendedMessageSubHeader, FullStateMessage | FullStateRequest
    ]
):
    """Encoder for the Full State Message and Request.

    A common encoder is used for the messages and requests because they share the
    same message ID.
    """

    @override
    def size(self, message: FullStateMessage | FullStateRequest) -> int:
        if isinstance(message, FullStateRequest):
            # No content for the FullStateRequest
            return 0

        return _FULL_STATE_MESSAGE_LENGTH

    @override
    def encode(
        self,
        header: x1F_ext.ExtendedMessageSubHeader,
        message: FullStateMessage | FullStateRequest,
    ) -> bytes:
        if isinstance(message, FullStateRequest):
            # The full state request has no content
            return b""

        buffer = bytearray()
        buffer.extend(
            _STRUCT.pack(
                self._encode_airtouch_id(message.airtouch_id),
                self._encode_version(message.hardware_version),
                self._encode_version(message.main_module_version),
            )
        )
        for _ in range(_AC_REPEAT_COUNT):
            buffer.extend(_AC_CONFIG_STRUCT.pack())
        for _ in range(_GROUP_REPEAT_COUNT):
            buffer.extend(_GROUP_NAME_STRUCT.pack(b""))
        buffer.extend(_UNKNOWN_STRUCT.pack())
        for _ in range(_AC_REPEAT_COUNT):
            buffer.extend(_AC_STATE_STRUCT.pack())
        for _ in range(_GROUP_REPEAT_COUNT):
            buffer.extend(_GROUP_STATE_STRUCT.pack())

        return bytes(buffer)

    def _encode_airtouch_id(self, airtouch_id: str) -> int:
        # The Airtouch ID is a Binary Coded Decimal (BCD) so convert from a hex string
        if len(airtouch_id) > _MAX_AIRTOUCH_ID_CHARACTERS:
            raise ValueError(
                f"airtouch_id '{airtouch_id}'"
                f" is longer than {_MAX_AIRTOUCH_ID_CHARACTERS} bytes"
            )
        return int(airtouch_id, 16)

    def _encode_version(self, version: str) -> int:
        # Version numbers are a series of 4 single hex characters with each pair
        # representing a byte, e.g.:
        # '1.2.a.b' => 0x12ab
        version_stripped = version.replace(".", "")
        if len(version_stripped) != _VERSION_CHARACTERS:
            raise ValueError(f"'{version}' is not a valid AirTouch version")
        return int(version_stripped, 16)


class FullStateDecoder(
    comms.MessageDecoder[
        x1F_ext.ExtendedMessageSubHeader,
        FullStateMessage | FullStateRequest,
    ]
):
    """Decoder for the Full State Message and Request.

    A common decoder is used for the message and request since they share the
    same message ID.
    """

    @override
    def decode(
        self, buffer: bytes | bytearray, header: x1F_ext.ExtendedMessageSubHeader
    ) -> MessageDecodeResult[FullStateMessage | FullStateRequest]:
        if header.message_length == 0:
            # If there is no content then this is a request for the full state.
            return comms.MessageDecodeResult(
                message=FullStateRequest(),
                remaining=bytes(buffer),
            )

        if header.message_length != _FULL_STATE_MESSAGE_LENGTH:
            raise comms.DecodeError(
                f"Message length ({header.message_length})"
                f" is not equal to expected value {_FULL_STATE_MESSAGE_LENGTH}"
            )

        (
            airtouch_id_raw,
            hardware_version_raw,
            main_module_version_raw,
        ) = _STRUCT.unpack_from(buffer)
        buffer = buffer[_STRUCT.size :]

        for _ in range(_AC_REPEAT_COUNT):
            _AC_CONFIG_STRUCT.unpack_from(buffer)
            buffer = buffer[_AC_CONFIG_STRUCT.size :]
        for _ in range(_GROUP_REPEAT_COUNT):
            _GROUP_NAME_STRUCT.unpack_from(buffer)
            buffer = buffer[_GROUP_NAME_STRUCT.size :]

        _ = _UNKNOWN_STRUCT.unpack_from(buffer)
        buffer = buffer[_UNKNOWN_STRUCT.size :]

        for _ in range(_AC_REPEAT_COUNT):
            _AC_STATE_STRUCT.unpack_from(buffer)
            buffer = buffer[_AC_STATE_STRUCT.size :]
        for _ in range(_GROUP_REPEAT_COUNT):
            _GROUP_STATE_STRUCT.unpack_from(buffer)
            buffer = buffer[_GROUP_STATE_STRUCT.size :]

        return comms.MessageDecodeResult(
            message=FullStateMessage(
                airtouch_id=self._decode_airtouch_id(airtouch_id_raw),
                hardware_version=self._decode_version(hardware_version_raw),
                main_module_version=self._decode_version(main_module_version_raw),
            ),
            remaining=bytes(buffer),
        )

    def _decode_airtouch_id(self, airtouch_id_raw: int) -> str:
        # The Airtouch ID is a Binary Coded Decimal (BCD), so just convert to hex
        return f"{airtouch_id_raw:X}"

    def _decode_version(self, version_raw: int) -> str:
        # Version numbers are just the individual hex characters separated by dots
        version_stripped = f"{version_raw:04X}"
        if len(version_stripped) > _VERSION_CHARACTERS:
            raise comms.DecodeError(f"Version '{version_stripped}' is too long")
        return ".".join(version_stripped)
