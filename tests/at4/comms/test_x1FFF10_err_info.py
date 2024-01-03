"""Tests the AC Error Information Message encoder and decoder."""  # noqa: N999

import pytest
from pyairtouch.at4.comms import x1F_ext
from pyairtouch.at4.comms.x1FFF10_err_info import (
    MESSAGE_ID,
    AcErrorInformationDecoder,
    AcErrorInformationEncoder,
    AcErrorInformationMessage,
    AcErrorInformationRequest,
)


def generate_header(
    message: AcErrorInformationMessage | AcErrorInformationRequest,
) -> x1F_ext.ExtendedMessageSubHeader:
    encoder = AcErrorInformationEncoder()
    return x1F_ext.ExtendedMessageSubHeader(
        message_id=MESSAGE_ID, message_length=encoder.size(message)
    )


@pytest.mark.parametrize(
    argnames=["message", "message_buffer"],
    argvalues=[
        #
        # Examples from the interface specification
        #
        (
            AcErrorInformationRequest(0),
            bytes((0x00,)),
        ),
        (
            AcErrorInformationMessage(
                ac_number=0,
                error_info="ER: FFFE",
            ),
            bytes((0x00, 0x08, 0x45, 0x52, 0x3A, 0x20, 0x46, 0x46, 0x46, 0x45)),
        ),
        #
        # Non-Zero AC Number and empty error info
        #
        (
            AcErrorInformationMessage(
                ac_number=3,
                error_info=None,
            ),
            bytes((0x03, 0x00)),
        ),
    ],
)
class TestAcErrorEncoderDecoder:
    def test_encoder(
        self,
        message: AcErrorInformationMessage | AcErrorInformationRequest,
        message_buffer: bytes,
    ) -> None:
        encoder = AcErrorInformationEncoder()
        header = generate_header(message)

        encoded_buffer = encoder.encode(header, message)

        assert message_buffer == encoded_buffer

    def test_decoder(
        self,
        message: AcErrorInformationMessage | AcErrorInformationRequest,
        message_buffer: bytes,
    ) -> None:
        decoder = AcErrorInformationDecoder()
        header = generate_header(message)

        decode_result = decoder.decode(message_buffer, header)

        decode_result.assert_complete()
        assert message == decode_result.message
