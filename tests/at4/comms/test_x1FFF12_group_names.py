"""Tests the encoder and decoder for the Group Names Message."""  # noqa: N999

import pytest
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x1FFF12_group_names import (
    MESSAGE_ID,
    GroupNamesDecoder,
    GroupNamesEncoder,
    GroupNamesMessage,
    GroupNamesRequest,
)


def generate_header(
    message: GroupNamesMessage | GroupNamesRequest,
) -> x1F_ext.ExtendedMessageSubHeader:
    encoder = GroupNamesEncoder()
    return x1F_ext.ExtendedMessageSubHeader(
        message_id=MESSAGE_ID,
        message_length=encoder.size(message),
    )


@pytest.mark.parametrize(
    argnames=["message", "message_buffer"],
    argvalues=[
        #
        # Requests
        #
        (
            GroupNamesRequest(group_number="ALL"),
            b"",
        ),
        (
            GroupNamesRequest(group_number=3),
            bytes((0x03,)),
        ),
        #
        # Group Names
        #
        (
            GroupNamesMessage(
                group_names={
                    1: "TEST 1",
                }
            ),
            b"\x01TEST 1\x00\x00",
        ),
        (
            GroupNamesMessage(
                group_names={
                    1: "TEST 1",
                    5: "",  # Empty and un-ordered group numbers
                    2: "TESTING2",  # Max length
                }
            ),
            b"\x01TEST 1\x00\x00"
            b"\x05\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x02TESTING2",
        ),
    ],
)
class TestGroupNamesEncoderDecoder:
    def test_encoder(
        self, message: GroupNamesMessage | GroupNamesRequest, message_buffer: bytes
    ) -> None:
        encoder = GroupNamesEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self, message: GroupNamesMessage | GroupNamesRequest, message_buffer: bytes
    ) -> None:
        decoder = GroupNamesDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
