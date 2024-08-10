"""Tests for the AC Ability encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x1FFF11_ac_ability import (
    MESSAGE_ID,
    AcAbility,
    AcAbilityDecoder,
    AcAbilityEncoder,
    AcAbilityMessage,
    AcAbilityRequest,
)
from pyairtouch.at4.comms.x2C_ac_ctrl import AcFanSpeedControl, AcModeControl


def generate_header(
    message: AcAbilityMessage | AcAbilityRequest,
) -> x1F_ext.ExtendedMessageSubHeader:
    encoder = AcAbilityEncoder()
    return x1F_ext.ExtendedMessageSubHeader(
        message_id=MESSAGE_ID,
        message_length=encoder.size(message),
    )


@pytest.mark.parametrize(
    argnames=["message", "message_buffer"],
    argvalues=[
        #
        # Examples from the interface specification v1.1.
        #
        (
            AcAbilityRequest(ac_number=0),
            bytes((0x00,)),
        ),
        (
            AcAbilityMessage(
                ac_abilities=[
                    AcAbility(
                        ac_number=0,
                        ac_name="UNIT",
                        # Example says cool, heat, fan, and auto mode,
                        # but the data is for cool, heat, dry, and auto modes.
                        # We assume the example description is incorrect and the
                        # spec is correct since tht specification aligns with
                        # the ordering in the AC Control message.
                        ac_mode_support={
                            AcModeControl.AUTO: True,
                            AcModeControl.HEAT: True,
                            AcModeControl.DRY: True,
                            AcModeControl.FAN: False,
                            AcModeControl.COOL: True,
                            AcModeControl.UNCHANGED: True,
                        },
                        fan_speed_support={
                            AcFanSpeedControl.AUTO: True,
                            AcFanSpeedControl.QUIET: False,
                            AcFanSpeedControl.LOW: True,
                            AcFanSpeedControl.MEDIUM: True,
                            AcFanSpeedControl.HIGH: True,
                            AcFanSpeedControl.POWERFUL: False,
                            AcFanSpeedControl.TURBO: False,
                            AcFanSpeedControl.UNCHANGED: True,
                        },
                        min_set_point=17,
                        max_set_point=31,
                        groups=None,
                        start_group=0,
                        group_count=4,
                    )
                ]
            ),
            # AC number and AC name
            b"\x00\x16\x55\x4e\x49\x54\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # Other data
            b"\x00\x04\x17\x1d\x11\x1f",
        ),
        #
        # Example from the interface specification v1.6.
        #
        (
            AcAbilityMessage(
                ac_abilities=[
                    AcAbility(
                        ac_number=0,
                        ac_name="UNIT",
                        # Example says cool, heat, fan, and auto mode,
                        # but the data is for cool, heat, dry, and auto modes.
                        # We assume the example description is incorrect and the
                        # spec is correct since tht specification aligns with
                        # the ordering in the AC Control message.
                        ac_mode_support={
                            AcModeControl.AUTO: True,
                            AcModeControl.HEAT: True,
                            AcModeControl.DRY: True,
                            AcModeControl.FAN: False,
                            AcModeControl.COOL: True,
                            AcModeControl.UNCHANGED: True,
                        },
                        fan_speed_support={
                            AcFanSpeedControl.AUTO: True,
                            AcFanSpeedControl.QUIET: False,
                            AcFanSpeedControl.LOW: True,
                            AcFanSpeedControl.MEDIUM: True,
                            AcFanSpeedControl.HIGH: True,
                            AcFanSpeedControl.POWERFUL: False,
                            AcFanSpeedControl.TURBO: False,
                            AcFanSpeedControl.UNCHANGED: True,
                        },
                        min_set_point=17,
                        max_set_point=31,
                        groups={0, 1, 2},
                        start_group=0,
                        group_count=4,
                    )
                ]
            ),
            # AC number and AC name
            b"\x00\x18\x55\x4e\x49\x54\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # Other data
            b"\x00\x04\x17\x1d\x11\x1f\x07\x00",
        ),
        #
        # AC Number and Start Group (console <v1.2.3)
        #
        (
            AcAbilityMessage(
                ac_abilities=[
                    AcAbility(
                        ac_number=2,
                        ac_name="TESTING",
                        ac_mode_support={
                            AcModeControl.AUTO: False,
                            AcModeControl.HEAT: False,
                            AcModeControl.DRY: False,
                            AcModeControl.FAN: False,
                            AcModeControl.COOL: False,
                            AcModeControl.UNCHANGED: True,
                        },
                        fan_speed_support={
                            AcFanSpeedControl.AUTO: False,
                            AcFanSpeedControl.QUIET: False,
                            AcFanSpeedControl.LOW: False,
                            AcFanSpeedControl.MEDIUM: False,
                            AcFanSpeedControl.HIGH: False,
                            AcFanSpeedControl.POWERFUL: False,
                            AcFanSpeedControl.TURBO: False,
                            AcFanSpeedControl.UNCHANGED: True,
                        },
                        min_set_point=0,
                        max_set_point=0,
                        groups=None,
                        start_group=3,
                        group_count=1,
                    )
                ]
            ),
            # AC number and AC name
            b"\x02\x16TESTING\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # Other data
            b"\x03\x01\x00\x00\x00\x00",
        ),
        #
        # Multiple ACs (console v1.2.3+)
        #
        (
            AcAbilityMessage(
                ac_abilities=[
                    AcAbility(
                        ac_number=0,
                        ac_name="The First",
                        ac_mode_support={
                            AcModeControl.AUTO: False,
                            AcModeControl.HEAT: True,
                            AcModeControl.DRY: False,
                            AcModeControl.FAN: False,
                            AcModeControl.COOL: True,
                            AcModeControl.UNCHANGED: True,
                        },
                        fan_speed_support={
                            AcFanSpeedControl.AUTO: False,
                            AcFanSpeedControl.QUIET: True,
                            AcFanSpeedControl.LOW: False,
                            AcFanSpeedControl.MEDIUM: False,
                            AcFanSpeedControl.HIGH: False,
                            AcFanSpeedControl.POWERFUL: True,
                            AcFanSpeedControl.TURBO: True,
                            AcFanSpeedControl.UNCHANGED: True,
                        },
                        min_set_point=12,
                        max_set_point=42,
                        groups={0, 1},
                        start_group=0,
                        group_count=0,
                    ),
                    AcAbility(
                        ac_number=1,
                        ac_name="Seconds",
                        ac_mode_support={
                            AcModeControl.AUTO: True,
                            AcModeControl.HEAT: True,
                            AcModeControl.DRY: False,
                            AcModeControl.FAN: True,
                            AcModeControl.COOL: True,
                            AcModeControl.UNCHANGED: True,
                        },
                        fan_speed_support={
                            AcFanSpeedControl.AUTO: True,
                            AcFanSpeedControl.QUIET: False,
                            AcFanSpeedControl.LOW: True,
                            AcFanSpeedControl.MEDIUM: True,
                            AcFanSpeedControl.HIGH: True,
                            AcFanSpeedControl.POWERFUL: False,
                            AcFanSpeedControl.TURBO: False,
                            AcFanSpeedControl.UNCHANGED: True,
                        },
                        min_set_point=18,
                        max_set_point=29,
                        groups={
                            2,
                        },
                        start_group=2,
                        # Observed in real-world examples the group count
                        # doesn't match the number of groups!
                        group_count=2,
                    ),
                ]
            ),
            # AC 0
            # AC number and AC name
            b"\x00\x18The First\x00\x00\x00\x00\x00\x00\x00"
            # Other data
            + bytes(
                (0x00, 0x00, 0b00010010, 0b01100010, 12, 42, 0b00000011, 0b00000000)
            )
            # AC 1
            # AC number and AC name
            + b"\x01\x18Seconds\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # Other data
            + bytes(
                (0x02, 0x02, 0b00011011, 0b00011101, 18, 29, 0b00000100, 0b00000000)
            ),
        ),
        (
            AcAbilityMessage(
                ac_abilities=[
                    AcAbility(
                        ac_number=3,
                        ac_name="A",
                        ac_mode_support={
                            AcModeControl.AUTO: False,
                            AcModeControl.HEAT: True,
                            AcModeControl.DRY: False,
                            AcModeControl.FAN: False,
                            AcModeControl.COOL: True,
                            AcModeControl.UNCHANGED: True,
                        },
                        fan_speed_support={
                            AcFanSpeedControl.AUTO: False,
                            AcFanSpeedControl.QUIET: True,
                            AcFanSpeedControl.LOW: False,
                            AcFanSpeedControl.MEDIUM: False,
                            AcFanSpeedControl.HIGH: False,
                            AcFanSpeedControl.POWERFUL: True,
                            AcFanSpeedControl.TURBO: True,
                            AcFanSpeedControl.UNCHANGED: True,
                        },
                        min_set_point=12,
                        max_set_point=42,
                        groups={10, 14},
                        start_group=0,
                        group_count=0,
                    ),
                    AcAbility(
                        ac_number=1,
                        ac_name="Seconds~`*/-=+#$",
                        ac_mode_support={
                            AcModeControl.AUTO: True,
                            AcModeControl.HEAT: True,
                            AcModeControl.DRY: False,
                            AcModeControl.FAN: True,
                            AcModeControl.COOL: True,
                            AcModeControl.UNCHANGED: True,
                        },
                        fan_speed_support={
                            AcFanSpeedControl.AUTO: True,
                            AcFanSpeedControl.QUIET: False,
                            AcFanSpeedControl.LOW: True,
                            AcFanSpeedControl.MEDIUM: True,
                            AcFanSpeedControl.HIGH: True,
                            AcFanSpeedControl.POWERFUL: False,
                            AcFanSpeedControl.TURBO: False,
                            AcFanSpeedControl.UNCHANGED: True,
                        },
                        min_set_point=18,
                        max_set_point=29,
                        groups={2, 7, 13},
                        start_group=0,
                        group_count=0,
                    ),
                ]
            ),
            # AC 3
            # AC number and AC name
            b"\x03\x18A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # Other data
            + bytes(
                (0x00, 0x00, 0b00010010, 0b01100010, 12, 42, 0b00000000, 0b01000100)
            )
            # AC 1
            # AC number and AC name
            + b"\x01\x18Seconds~`*/-=+#$"
            # Other data
            + bytes(
                (0x00, 0x00, 0b00011011, 0b00011101, 18, 29, 0b10000100, 0b00100000)
            ),
        ),
    ],
)
class TestAcAbilityEncoderDecoder:
    def test_encoder(
        self, message: AcAbilityMessage | AcAbilityRequest, message_buffer: bytes
    ) -> None:
        encoder = AcAbilityEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self, message: AcAbilityMessage | AcAbilityRequest, message_buffer: bytes
    ) -> None:
        decoder = AcAbilityDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
