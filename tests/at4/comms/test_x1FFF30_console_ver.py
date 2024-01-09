"""Tests the encoder and decoder for the Console Version Message."""  # noqa: N999

import pytest
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x1FFF30_console_ver import (
    MESSAGE_ID,
    ConsoleVersionDecoder,
    ConsoleVersionEncoder,
    ConsoleVersionMessage,
    ConsoleVersionRequest,
)


def generate_header(
    message: ConsoleVersionMessage | ConsoleVersionRequest,
) -> x1F_ext.ExtendedMessageSubHeader:
    encoder = ConsoleVersionEncoder()
    return x1F_ext.ExtendedMessageSubHeader(
        message_id=MESSAGE_ID, message_length=encoder.size(message)
    )


@pytest.mark.parametrize(
    argnames=["message", "message_buffer"],
    argvalues=[
        #
        # Request
        #
        (
            ConsoleVersionRequest(),
            b"",
        ),
        #
        # Example from the interface specification
        #
        (
            ConsoleVersionMessage(update_available=False, versions=["1.3.3", "1.3.3"]),
            b"\x00\x0b\x31\x2e\x33\x2e\x33\x7c\x31\x2e\x33\x2e\x33",
        ),
        #
        # One version and update available
        #
        (
            ConsoleVersionMessage(update_available=True, versions=["2.3.4"]),
            b"\x01\x052.3.4",
        ),
        #
        # Two different versions
        #
        (
            ConsoleVersionMessage(update_available=False, versions=["2.3.4", "98.7"]),
            b"\x00\x0a2.3.4|98.7",
        ),
    ],
)
class TestConsoleVersionEncoderDecoder:
    def test_encoder(
        self,
        message: ConsoleVersionMessage | ConsoleVersionRequest,
        message_buffer: bytes,
    ) -> None:
        encoder = ConsoleVersionEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self,
        message: ConsoleVersionMessage | ConsoleVersionRequest,
        message_buffer: bytes,
    ) -> None:
        decoder = ConsoleVersionDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
