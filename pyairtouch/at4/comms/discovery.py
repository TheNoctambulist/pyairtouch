"""AirTouch 4 discovery protocol implementation.

The AirTouch 4 discovery protocol is not document in the communication protocol
document. The implementation here has been reverse engineered using the AirTouch
5 documentation as a reference.
"""

from dataclasses import dataclass

from typing_extensions import override

from pyairtouch import comms
from pyairtouch.comms import encoding

PORT = 49004

_REQUEST_DATA = b"HF-A11ASSISTHREAD"

_RESPONSE_ID = b",AirTouch4,"
"""The unique identifier for the response is in the middle of the response string."""

# A discovery response is of the form:
# "<Host>,<Serial>,<Version>,<ID>"
_NUM_RESPONSE_PARTS = 4
_PART_HOST = 0
_PART_SERIAL = 1
_PART_RESPONSE_ID = 2
_PART_AIRTOUCH_ID = 3


# dataclass for automatic equality (even though there's no fields!)
@dataclass
class At4DiscoveryRequest(comms.DiscoveryRequest):
    """The discovery request for the AirTouch 4."""

    @override
    @property
    def data(self) -> bytes:
        return _REQUEST_DATA


# Implements comms.DiscoveryResponse via structual typing to avoid runtime errors.
# See https://bugs.python.org/issue47237
@dataclass(frozen=True)
class At4DiscoveryResponse:
    """Response to an AirTouch 4 discovery request."""

    airtouch_id: str
    """The ID of the AirTouch system."""
    host: str
    """The host name or IP address of the AirTouch console."""
    serial: str
    """The serial number of the AirTouch console."""


class At4DiscoveryDecoder(
    comms.DiscoveryDecoder[At4DiscoveryRequest, At4DiscoveryResponse]
):
    """Decoder for AirTouch 4 discovery messages."""

    @override
    def match(self, buffer: bytes | bytearray) -> bool:
        return buffer == _REQUEST_DATA or _RESPONSE_ID in buffer

    @override
    def decode(
        self, buffer: bytes | bytearray
    ) -> At4DiscoveryRequest | At4DiscoveryResponse:
        if buffer == _REQUEST_DATA:
            return At4DiscoveryRequest()

        response_raw = buffer.split(b",", _NUM_RESPONSE_PARTS - 1)

        if len(response_raw) != _NUM_RESPONSE_PARTS:
            raise comms.DecodeError(
                f"Response didn't include the expected number of parts: {buffer!r}"
            )

        if response_raw[_PART_RESPONSE_ID] != _RESPONSE_ID.strip(b","):
            raise comms.DecodeError(
                f"Response ID was not in the expected location: {buffer!r}"
            )

        return At4DiscoveryResponse(
            airtouch_id=response_raw[_PART_AIRTOUCH_ID].decode(
                encoding=encoding.STRING_ENCODING
            ),
            serial=response_raw[_PART_SERIAL].decode(encoding=encoding.STRING_ENCODING),
            host=response_raw[_PART_HOST].decode(encoding=encoding.STRING_ENCODING),
        )


CONFIG = comms.DiscoveryConfig(
    local_port=PORT,
    remote_port=PORT,
    request_factory=At4DiscoveryRequest,
    response_type=At4DiscoveryResponse,
    decoder=At4DiscoveryDecoder(),
)
