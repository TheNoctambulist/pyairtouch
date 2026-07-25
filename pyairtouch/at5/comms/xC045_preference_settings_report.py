"""Definition of the Preference Settings Report Message (0xC045).

Preference Settings Report messages provide the device information.

The contents of this message have been reverse engineered.
"""  # noqa: N999

import logging
import struct
from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.at5.comms import xC0_ctrl_status
from pyairtouch.comms import encoding, log

MESSAGE_ID = 0x45

_LOGGER = logging.getLogger(__name__)


@dataclass
class PreferenceSettingsReportMessage(comms.Message):
    """The Preference Settings Report Message."""

    system_name: str
    airtouch_id: str
    hardware_version: str
    main_module_version: str
    boot_version: str

    @property
    @override
    def message_id(self) -> int:
        return MESSAGE_ID


@dataclass
class PreferenceSettingsReportRequest(comms.Message):
    """Request for Preference Settings Report."""

    @property
    @override
    def message_id(self) -> int:
        return MESSAGE_ID


# Struct includes padding bytes for unknown fields.
# These are not always zero when received.
_STRUCT = struct.Struct("!16s24xLHHH2x")

_VERSION_CHARACTERS = 4
_MAX_AIRTOUCH_ID_CHARACTERS = 8


class PreferenceSettingsReportEncoder(
    xC0_ctrl_status.ControlStatusSubEncoder[
        PreferenceSettingsReportMessage | PreferenceSettingsReportRequest
    ]
):
    """Encoder for the Preference Settings Report Message and Request.

    Handles both the message and request since they have the same message ID.
    """

    @override
    def non_repeat_size(
        self, message: PreferenceSettingsReportMessage | PreferenceSettingsReportRequest
    ) -> int:
        if isinstance(message, PreferenceSettingsReportRequest):
            return 0
        return 52

    @override
    def repeat_count(
        self, message: PreferenceSettingsReportMessage | PreferenceSettingsReportRequest
    ) -> int:
        # No repeating data
        return 0

    @override
    def repeat_size(
        self, message: PreferenceSettingsReportMessage | PreferenceSettingsReportRequest
    ) -> int:
        return 0

    @override
    def encode(
        self,
        header: xC0_ctrl_status.ControlStatusSubHeader,
        message: PreferenceSettingsReportMessage | PreferenceSettingsReportRequest,
    ) -> bytes:
        if isinstance(message, PreferenceSettingsReportRequest):
            # PreferenceSettingsReportRequest has no content
            return b""

        buffer = bytearray()

        encoded_airtouch_id = self._encode_airtouch_id(message.airtouch_id)
        encoded_hardware_version = self._encode_version(message.hardware_version)
        encoded_main_module_version = self._encode_version(message.main_module_version)
        encoded_boot_version = self._encode_version(message.boot_version)

        buffer.extend(
            _STRUCT.pack(
                message.system_name.encode(encoding.STRING_ENCODING),
                encoded_airtouch_id,
                encoded_hardware_version,
                encoded_main_module_version,
                encoded_boot_version,
            )
        )

        return bytes(buffer)

    def _encode_airtouch_id(self, airtouch_id: str) -> int:
        # The Airtouch ID is a Binary Coded Decimal (BCD), so convert from a hex string
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


class PreferenceSettingsReportDecoder(
    comms.MessageDecoder[
        xC0_ctrl_status.ControlStatusSubHeader,
        PreferenceSettingsReportMessage | PreferenceSettingsReportRequest,
    ]
):
    """Decoder for the Preference Settings Report Message and Request."""

    def __init__(self) -> None:
        """Initialise the PreferenceSettingsReportDecoder."""
        # Avoid repeated logging of message length mismatches if the console has
        # an upgraded protocol.
        self._length_mismatch_event = log.LogEvent(_LOGGER, logging.INFO)

    @override
    def decode(
        self, buffer: bytes | bytearray, header: xC0_ctrl_status.ControlStatusSubHeader
    ) -> comms.MessageDecodeResult[
        PreferenceSettingsReportMessage | PreferenceSettingsReportRequest
    ]:
        if header.non_repeat_length == 0:
            return comms.MessageDecodeResult(
                message=PreferenceSettingsReportRequest(), remaining=bytes(buffer)
            )

        # Otherwise decode the Preference Settings Report:
        if header.non_repeat_length < _STRUCT.size:
            raise comms.DecodeError(
                f"Message length ({header.non_repeat_length}) < "
                f"Preference Settings Report data size ({_STRUCT.size})"
            )

        if header.non_repeat_length != _STRUCT.size:
            self._length_mismatch_event.log(
                "Header non_repeat_length (%d) != "
                "Preference Settings Report data size (%d). "
                "Ignoring extra bytes",
                header.non_repeat_length,
                _STRUCT.size,
            )

        (
            system_name_raw,
            airtouch_id_raw,
            hardware_version_raw,
            main_module_version_raw,
            boot_version_raw,
        ) = _STRUCT.unpack_from(buffer)
        buffer = buffer[header.non_repeat_length :]

        return comms.MessageDecodeResult(
            message=PreferenceSettingsReportMessage(
                system_name=encoding.decode_c_string(system_name_raw),
                airtouch_id=self._decode_airtouch_id(airtouch_id_raw),
                hardware_version=self._decode_version(hardware_version_raw),
                main_module_version=self._decode_version(main_module_version_raw),
                boot_version=self._decode_version(boot_version_raw),
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
