"""Tests for the Preference Settings Report message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at5.comms.xC0_ctrl_status import ControlStatusSubHeader
from pyairtouch.at5.comms.xC045_preference_settings_report import (
    MESSAGE_ID,
    PreferenceSettingsReportDecoder,
    PreferenceSettingsReportEncoder,
    PreferenceSettingsReportMessage,
    PreferenceSettingsReportRequest,
)


def generate_header(
    message: PreferenceSettingsReportMessage | PreferenceSettingsReportRequest,
) -> ControlStatusSubHeader:
    """Construct a header for the PreferenceSettingsReportMessage."""
    encoder = PreferenceSettingsReportEncoder()
    return ControlStatusSubHeader(
        sub_message_id=MESSAGE_ID,
        non_repeat_length=encoder.non_repeat_size(message),
        repeat_length=encoder.repeat_size(message),
        repeat_count=encoder.repeat_count(message),
    )


_common_parameterizations = [
    #
    # Request
    #
    (PreferenceSettingsReportRequest(), bytes(())),
    #
    # Message
    #
    (
        PreferenceSettingsReportMessage(
            system_name="system",
            airtouch_id="91234567",
            hardware_version="1.2.3.4",
            main_module_version="9.8.7.6",
            boot_version="A.B.C.D",
        ),
        (
            b"system\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x91\x23\x45\x67"
            b"\x12\x34\x98\x76"
            b"\xab\xcd"
            b"\x00\x00"
        ),
    ),
]


class TestPreferenceSettingsReportEncoderDecoder:
    @pytest.mark.parametrize(
        argnames=("message", "message_buffer"),
        argvalues=[
            *_common_parameterizations,
        ],
    )
    def test_encoder(
        self,
        message: PreferenceSettingsReportMessage | PreferenceSettingsReportRequest,
        message_buffer: bytes,
    ) -> None:
        encoder = PreferenceSettingsReportEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    @pytest.mark.parametrize(
        argnames=("message", "message_buffer"),
        argvalues=[
            *_common_parameterizations,
            #
            # Real observed message
            #
            (
                PreferenceSettingsReportMessage(
                    system_name="AirTouch 5",
                    airtouch_id="90234567",
                    hardware_version="2.3.0.E",
                    main_module_version="2.0.1.6",
                    boot_version="0.0.0.0",  # noqa: S104 Ruff thinks this is an IP address
                ),
                (
                    b"\x41\x69\x72\x54\x6f\x75\x63\x68\x20\x35\x00\x00\x00\x00\x00\x00"
                    b"\x14\x00\x00\x00\x1c\x0f\x1b\x12\x00\x00\x00\x00\x00\x00\x00\x00\x41\x74\x63\x68\x56\x35\x4d\x00"
                    b"\x90\x23\x45\x67"
                    b"\x23\x0e\x20\x16\x00\x00"
                    b"\x00\x00"
                ),
            ),
        ],
    )
    def test_decoder(
        self,
        message: PreferenceSettingsReportMessage | PreferenceSettingsReportRequest,
        message_buffer: bytes,
    ) -> None:
        decoder = PreferenceSettingsReportDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
