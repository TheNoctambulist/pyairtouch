"""Tests the encoder and decoder for the Full State Message."""  # noqa: N999

import pytest
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x2F03FF_full_state import (
    MESSAGE_ID,
    FullStateDecoder,
    FullStateEncoder,
    FullStateMessage,
    FullStateRequest,
)


def generate_header(
    message: FullStateMessage | FullStateRequest,
) -> x1F_ext.ExtendedMessageSubHeader:
    encoder = FullStateEncoder()
    return x1F_ext.ExtendedMessageSubHeader(
        message_id=MESSAGE_ID, message_length=encoder.size(message)
    )


@pytest.mark.parametrize(
    argnames=("message", "message_buffer"),
    argvalues=[
        #
        # Request
        #
        (
            FullStateRequest(),
            b"",
        ),
        #
        # Message
        #
        (
            FullStateMessage(
                airtouch_id="81234567",
                hardware_version="1.2.3.4",
                main_module_version="9.8.7.6",
            ),
            (
                b"\x81\x23\x45\x67\x12\x34\x98\x76"
                + b"\x00" * 52  # Spare bytes for initial state
                + b"\x00" * 18 * 4  # AC Config
                + b"\x00" * 8 * 16  # Group Names
                + b"\x00" * 62  # Unknown data
                + b"\x00" * 8 * 4  # AC State
                + b"\x00" * 6 * 16  # Group State
            ),
        ),
    ],
)
class TestFullStateEncoderDecoder:
    def test_encoder(
        self,
        message: FullStateMessage | FullStateRequest,
        message_buffer: bytes,
    ) -> None:
        encoder = FullStateEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self,
        message: FullStateMessage | FullStateRequest,
        message_buffer: bytes,
    ) -> None:
        decoder = FullStateDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
