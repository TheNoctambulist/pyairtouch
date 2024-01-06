"""Defines the Message Registry for the AirTouch 5 protocol.

The MessageRegistry is available via the module INSTANCE variable and contains
encoders and decoders for all known AirTouch 5 messages.
"""

from typing_extensions import override

import pyairtouch.comms.crc16
from pyairtouch import comms

from . import (
    hdr,
    x1F_ext,
    x1FFF10_err_info,
    x1FFF11_ac_ability,
    x1FFF13_zone_names,
    x1FFF30_console_ver,
    xC0_ctrl_status,
    xC020_zone_ctrl,
    xC021_zone_status,
    xC022_ac_ctrl,
    xC023_ac_status,
)


class HeaderFactory(comms.HeaderFactory[hdr.At5Header]):
    """A factory for creating AirTouch 5 headers."""

    def __init__(self) -> None:
        """Initialise the header factory."""
        self._next_packet_id = 0

    @override
    def create_from_message(
        self, message: comms.Message, message_length: int
    ) -> hdr.At5Header:
        message_id = message.message_id

        # The "To" address depends whether we are sending an extended message or not.
        to_address = hdr.ADDRESS_AIRTOUCH
        if message_id == x1F_ext.MESSAGE_ID:
            to_address = hdr.ADDRESS_AIRTOUCH_EXTENDED

        return hdr.At5Header(
            to_address=to_address,
            from_address=hdr.ADDRESS_CLIENT,
            packet_id=self._packet_id(),
            message_id=message_id,
            message_length=message_length,
        )

    def _packet_id(self) -> int:
        packet_id = self._next_packet_id
        self._next_packet_id = (self._next_packet_id + 1) % 256
        return packet_id


INSTANCE = comms.MessageRegistry(
    header_factory=HeaderFactory(),
    header_encoder=hdr.HeaderEncoder(),
    header_decoder=hdr.HeaderDecoder(),
    checksum_calculator=pyairtouch.comms.crc16.Crc16Modbus(),
)
"""The AirTouch 5 Message Registry"""

#
# Extended Message Registration
#
_extended_encoder = x1F_ext.ExtendedMessageEncoder(
    {
        x1FFF10_err_info.MESSAGE_ID: x1FFF10_err_info.AcErrorInformationEncoder(),
        x1FFF11_ac_ability.MESSAGE_ID: x1FFF11_ac_ability.AcAbilityEncoder(),
        x1FFF13_zone_names.MESSAGE_ID: x1FFF13_zone_names.ZoneNamesEncoder(),
        x1FFF30_console_ver.MESSAGE_ID: x1FFF30_console_ver.ConsoleVersionEncoder(),
    }
)
_extended_decoder = x1F_ext.ExtendedMessageDecoder(
    {
        x1FFF10_err_info.MESSAGE_ID: x1FFF10_err_info.AcErrorInformationDecoder(),
        x1FFF11_ac_ability.MESSAGE_ID: x1FFF11_ac_ability.AcAbilityDecoder(),
        x1FFF13_zone_names.MESSAGE_ID: x1FFF13_zone_names.ZoneNamesDecoder(),
        x1FFF30_console_ver.MESSAGE_ID: x1FFF30_console_ver.ConsoleVersionDecoder(),
    }
)

INSTANCE.register(
    message_id=x1F_ext.MESSAGE_ID,
    encoder=_extended_encoder,
    decoder=_extended_decoder,
)

#
# Control/Status Message Registration
#
_ctrl_status_encoder = xC0_ctrl_status.ControlStatusEncoder(
    {
        xC020_zone_ctrl.MESSAGE_ID: xC020_zone_ctrl.ZoneControlEncoder(),
        xC021_zone_status.MESSAGE_ID: xC021_zone_status.ZoneStatusEncoder(),
        xC022_ac_ctrl.MESSAGE_ID: xC022_ac_ctrl.AcControlEncoder(),
        xC023_ac_status.MESSAGE_ID: xC023_ac_status.AcStatusEncoder(),
    }
)
_ctrl_status_decoder = xC0_ctrl_status.ControlStatusDecoder(
    {
        xC020_zone_ctrl.MESSAGE_ID: xC020_zone_ctrl.ZoneControlDecoder(),
        xC021_zone_status.MESSAGE_ID: xC021_zone_status.ZoneStatusDecoder(),
        xC022_ac_ctrl.MESSAGE_ID: xC022_ac_ctrl.AcControlDecoder(),
        xC023_ac_status.MESSAGE_ID: xC023_ac_status.AcStatusDecoder(),
    }
)

INSTANCE.register(
    message_id=xC0_ctrl_status.MESSAGE_ID,
    encoder=_ctrl_status_encoder,
    decoder=_ctrl_status_decoder,
)
