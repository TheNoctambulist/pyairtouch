"""Defines the Message Registry for the AirTouch 4 protocol.

The MessageRegistry is available via the module INSTANCE variable and contains
encoders and decoders for all known AirTouch 5 messages.
"""

from typing_extensions import override

import pyairtouch.comms.crc16
from pyairtouch import comms
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.comms import Message

from . import (
    hdr,
    x1F_ext,
    x1FFF10_err_info,
    x1FFF11_ac_ability,
    x1FFF12_group_names,
    x2A_group_ctrl,
    x2B_group_status,
    x2C_ac_ctrl,
    x2D_ac_status,
)


class HeaderFactory(comms.HeaderFactory[hdr.At4Header]):
    """A factory for creating AirTouch 4 headers."""

    def __init__(self) -> None:
        """Initialise the header factory."""
        self._next_packet_id = 0

    @override
    def create_from_message(self, message: Message, message_length: int) -> At4Header:
        message_id = message.message_id

        # The "To" address depends whether we are sending an extended message or not.
        to_address = hdr.ADDRESS_AIRTOUCH
        if message_id == x1F_ext.MESSAGE_ID:
            to_address = hdr.ADDRESS_AIRTOUCH_EXTENDED

        return hdr.At4Header(
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
"""The AirTouch 4 Message Registry."""

#
# Extended Message Registration
#
_extended_encoder = x1F_ext.ExtendedMessageEncoder(
    encoder_map={
        x1FFF10_err_info.MESSAGE_ID: x1FFF10_err_info.AcErrorInformationEncoder(),
        x1FFF11_ac_ability.MESSAGE_ID: x1FFF11_ac_ability.AcAbilityEncoder(),
        x1FFF12_group_names.MESSAGE_ID: x1FFF12_group_names.GroupNamesEncoder(),
    }
)
_extended_decoder = x1F_ext.ExtendedMessageDecoder(
    decoder_map={
        x1FFF10_err_info.MESSAGE_ID: x1FFF10_err_info.AcErrorInformationDecoder(),
        x1FFF11_ac_ability.MESSAGE_ID: x1FFF11_ac_ability.AcAbilityDecoder(),
        x1FFF12_group_names.MESSAGE_ID: x1FFF12_group_names.GroupNamesDecoder(),
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
INSTANCE.register(
    message_id=x2A_group_ctrl.MESSAGE_ID,
    encoder=x2A_group_ctrl.GroupControlEncoder(),
    decoder=x2A_group_ctrl.GroupControlDecoder(),
)
INSTANCE.register(
    message_id=x2B_group_status.MESSAGE_ID,
    encoder=x2B_group_status.GroupStatusEncoder(),
    decoder=x2B_group_status.GroupStatusDecoder(),
)
INSTANCE.register(
    message_id=x2C_ac_ctrl.MESSAGE_ID,
    encoder=x2C_ac_ctrl.AcControlEncoder(),
    decoder=x2C_ac_ctrl.AcControlDecoder(),
)
INSTANCE.register(
    message_id=x2D_ac_status.MESSAGE_ID,
    encoder=x2D_ac_status.AcStatusEncoder(),
    decoder=x2D_ac_status.AcStatusDecoder(),
)
