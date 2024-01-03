"""Tests for the Group Control Message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at4.comms.hdr import At4Header
from pyairtouch.at4.comms.x2A_group_ctrl import (
    MESSAGE_ID,
    GroupControlDecoder,
    GroupControlEncoder,
    GroupControlMessage,
    GroupControlMethod,
    GroupDamperControl,
    GroupIncreaseDecrease,
    GroupPowerControl,
    GroupSetPointControl,
)


def generate_header(message: GroupControlMessage) -> At4Header:
    encoder = GroupControlEncoder()
    return At4Header(
        to_address=0,
        from_address=0,
        packet_id=0,
        message_id=MESSAGE_ID,
        message_length=encoder.size(message),
    )


@pytest.mark.parametrize(
    argnames=["message", "message_buffer"],
    argvalues=[
        #
        # Example messages from the interface specification.
        #
        (
            GroupControlMessage(
                group_number=1,
                power=GroupPowerControl.TURN_OFF,
                control_method=GroupControlMethod.UNCHANGED,
                setting=None,
            ),
            bytes((0x01, 0x02, 0x00, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.DAMPER,
                setting=None,
            ),
            bytes((0x00, 0x10, 0x00, 0x00)),
        ),
        #
        # Power Control
        #
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.TOGGLE,
                control_method=GroupControlMethod.UNCHANGED,
                setting=None,
            ),
            bytes((0x00, 0b00000001, 0x00, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.TURN_ON,
                control_method=GroupControlMethod.UNCHANGED,
                setting=None,
            ),
            bytes((0x00, 0b00000011, 0x00, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.TURBO,
                control_method=GroupControlMethod.UNCHANGED,
                setting=None,
            ),
            bytes((0x00, 0b00000101, 0x00, 0x00)),
        ),
        #
        # Control Method
        #
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.CHANGE,
                setting=None,
            ),
            bytes((0x00, 0b00001000, 0x00, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.DAMPER,
                setting=None,
            ),
            bytes((0x00, 0b00010000, 0x00, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.TEMPERATURE,
                setting=None,
            ),
            bytes((0x00, 0b00011000, 0x00, 0x00)),
        ),
        #
        # Settings
        #
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.UNCHANGED,
                setting=GroupIncreaseDecrease.DECREASE,
            ),
            bytes((0x00, 0b01000000, 0x00, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.UNCHANGED,
                setting=GroupIncreaseDecrease.INCREASE,
            ),
            bytes((0x00, 0b01100000, 0x00, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.UNCHANGED,
                setting=GroupDamperControl(open_percentage=56),
            ),
            bytes((0x00, 0b10000000, 56, 0x00)),
        ),
        (
            GroupControlMessage(
                group_number=0,
                power=GroupPowerControl.UNCHANGED,
                control_method=GroupControlMethod.UNCHANGED,
                setting=GroupSetPointControl(set_point=23),
            ),
            bytes((0x00, 0b10100000, 23, 0x00)),
        ),
    ],
)
class TestGroupControlEncoderDecoder:
    def test_encoder(self, message: GroupControlMessage, message_buffer: bytes) -> None:
        encoder = GroupControlEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(self, message: GroupControlMessage, message_buffer: bytes) -> None:
        decoder = GroupControlDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
