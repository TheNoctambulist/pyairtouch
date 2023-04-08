import pytest
from pyairtouch import comms
from pyairtouch.at4.comms.discovery import (
    _RESPONSE_ID,
    At4DiscoveryDecoder,
    At4DiscoveryRequest,
    At4DiscoveryResponse,
)


def test_decode_request() -> None:
    decoder = At4DiscoveryDecoder()
    request = At4DiscoveryRequest()

    response = decoder.decode(request.data)

    assert response == request


def test_decode_response() -> None:
    decoder = At4DiscoveryDecoder()

    host = "10.1.2.3"
    serial = "456"
    airtouch_id = "789"
    # _RESPONSE ID includes separators.
    buffer = f"{host},{serial}{_RESPONSE_ID.decode()}{airtouch_id}".encode()

    response = decoder.decode(buffer)

    assert isinstance(response, At4DiscoveryResponse)
    assert host == response.host
    assert airtouch_id == response.airtouch_id
    assert serial == response.serial


def test_decode_invalid_order() -> None:
    decoder = At4DiscoveryDecoder()

    buffer = b"host" + _RESPONSE_ID + b",serial,airtouch_id"

    with pytest.raises(comms.DecodeError):
        decoder.decode(buffer)


def test_decode_invalid_too_few() -> None:
    decoder = At4DiscoveryDecoder()

    buffer = b"host,serial," + _RESPONSE_ID.strip(b",")

    with pytest.raises(comms.DecodeError):
        decoder.decode(buffer)
