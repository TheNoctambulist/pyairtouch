import pytest
from pyairtouch import comms
from pyairtouch.at5.comms.discovery import (
    _RESPONSE_ID,
    At5DiscoveryDecoder,
    At5DiscoveryRequest,
    At5DiscoveryResponse,
)


def test_decode_request() -> None:
    decoder = At5DiscoveryDecoder()
    request = At5DiscoveryRequest()

    response = decoder.decode(request.data)

    assert response == request


def test_decode_response() -> None:
    decoder = At5DiscoveryDecoder()

    host = "10.1.2.3"
    serial = "456"
    airtouch_id = "789"
    name = "Name"
    # _RESPONSE ID includes separators.
    buffer = f"{host},{serial}{_RESPONSE_ID.decode()}{airtouch_id},{name}".encode()

    response = decoder.decode(buffer)

    assert isinstance(response, At5DiscoveryResponse)
    assert host == response.host
    assert airtouch_id == response.airtouch_id
    assert serial == response.serial
    assert name == response.name


def test_decode_response_name_comma() -> None:
    decoder = At5DiscoveryDecoder()

    name = "Syst,em Name"
    buffer = f"abc,def{_RESPONSE_ID.decode()}ghi,{name}".encode()

    response = decoder.decode(buffer)

    assert isinstance(response, At5DiscoveryResponse)
    assert name == response.name


def test_decode_invalid_order() -> None:
    decoder = At5DiscoveryDecoder()

    buffer = b"host" + _RESPONSE_ID + b",serial,airtouch_id,name"

    with pytest.raises(comms.DecodeError):
        decoder.decode(buffer)


def test_decode_invalid_too_few() -> None:
    decoder = At5DiscoveryDecoder()

    buffer = b"host,serial" + _RESPONSE_ID + b"airtouch_id"

    with pytest.raises(comms.DecodeError):
        decoder.decode(buffer)
