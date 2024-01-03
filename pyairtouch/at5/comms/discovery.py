"""AirTouch 5 discovery protocol implementation.

Implements AirTouch 5 discovery in accordance with v1.1 of the communication
protocol.
"""

from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.comms import encoding

PORT = 49005

_REQUEST_DATA = b"::REQUEST-POLYAIRE-AIRTOUCH-DEVICE-INFO:;"

_RESPONSE_ID = b",AirTouch5,"
"""The unique identifier for the response is in the middle of the response string."""

# A discovery response is of the form:
# "<Host>,<Serial>,<Version>,<ID>,<Name>"
_NUM_RESPONSE_PARTS = 5
_PART_HOST = 0
_PART_SERIAL = 1
_PART_RESPONSE_ID = 2
_PART_AIRTOUCH_ID = 3
_PART_NAME = 4


# dataclass for automatic equality (even though there's no fields!)
@dataclass
class At5DiscoveryRequest(comms.DiscoveryRequest):
    """The discovery request for the AirTouch 5."""

    @override
    @property
    def data(self) -> bytes:
        return _REQUEST_DATA


# Implements comms.DiscoveryResponse via structual typing to avoid runtime errors.
# See https://bugs.python.org/issue47237
@dataclass(frozen=True)
class At5DiscoveryResponse:
    """Response to an AirTouch 5 discovery request."""

    airtouch_id: str
    """The ID of the AirTouch system."""
    name: str
    """The human readable name of the AirTouch system."""
    serial: str
    """The serial number of the AirTouch console."""
    host: str
    """The host name or IP address of the AirTouch console."""


class At5DiscoveryDecoder(
    comms.DiscoveryDecoder[At5DiscoveryRequest, At5DiscoveryResponse]
):
    """Decoder for AirTouch 5 discovery messages."""

    @override
    def match(self, buffer: bytes | bytearray) -> bool:
        return buffer == _REQUEST_DATA or _RESPONSE_ID in buffer

    @override
    def decode(
        self, buffer: bytes | bytearray
    ) -> At5DiscoveryRequest | At5DiscoveryResponse:
        if buffer == _REQUEST_DATA:
            return At5DiscoveryRequest()

        response_raw = buffer.split(b",", _NUM_RESPONSE_PARTS - 1)

        if len(response_raw) != _NUM_RESPONSE_PARTS:
            raise comms.DecodeError(
                f"Response didn't include the expected number of parts: {buffer!r}"
            )

        if response_raw[_PART_RESPONSE_ID] != _RESPONSE_ID.strip(b","):
            raise comms.DecodeError(
                f"Response ID was not in the expected location: {buffer!r}"
            )

        return At5DiscoveryResponse(
            airtouch_id=response_raw[_PART_AIRTOUCH_ID].decode(
                encoding=encoding.STRING_ENCODING
            ),
            name=response_raw[_PART_NAME].decode(encoding=encoding.STRING_ENCODING),
            serial=response_raw[_PART_SERIAL].decode(encoding=encoding.STRING_ENCODING),
            host=response_raw[_PART_HOST].decode(encoding=encoding.STRING_ENCODING),
        )


CONFIG = comms.DiscoveryConfig(
    local_port=PORT,
    remote_port=PORT,
    request_factory=At5DiscoveryRequest,
    response_type=At5DiscoveryResponse,
    decoder=At5DiscoveryDecoder(),
)
