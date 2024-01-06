"""AirTouch Communication interfaces.

Defines the interfaces for interfacing with the AirTouch including common
encoding/decoding utilities shared by multiple AirTouch versions.
"""


from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from typing_extensions import override


class EncodeError(Exception):
    """Raised when an error occurs encoding to a buffer."""


class DecodeError(Exception):
    """Raised when an error occurs decoding from a buffer."""


class Header(Protocol):
    """Defines the interface for headers wrapping a message."""

    @property
    def message_id(self) -> int:
        """ID of the wrapped message."""

    @property
    def message_length(self) -> int:
        """Length of the message (excluding header) in bytes."""


Hdr = TypeVar("Hdr", bound=Header)
Hdr_co = TypeVar("Hdr_co", bound=Header, covariant=True)
Hdr_contra = TypeVar("Hdr_contra", bound=Header, contravariant=True)


class Message(Protocol):
    """Defines the interface for messages."""

    @property
    def message_id(self) -> int:
        """The message's ID."""


Msg = TypeVar("Msg", bound=Message)
Msg_co = TypeVar("Msg_co", bound=Message, covariant=True)
Msg_contra = TypeVar("Msg_contra", bound=Message, contravariant=True)


@dataclass
class HeaderEncodeResult:
    """The result from a header encode operation.

    Includes fields to capture the encoded data and the subset of bytes to
    include in the checksum data.
    """

    header_bytes: bytes
    """The encoded header."""

    checksum_data: bytes
    """The bytes from the header that contribute to the checksum."""


class HeaderEncoder(Protocol[Hdr_contra]):
    """Interface for header encoders."""

    def encode(self, header: Hdr_contra) -> HeaderEncodeResult:
        """Encodes the header into a sequence of bytes."""


@dataclass
class HeaderDecodeResult(Generic[Hdr_co]):
    """The result from a header decode operation.

    Includes fields to capture the decoded data, checksum data, and any
    remaining bytes that were not decoded.
    """

    header: Hdr_co
    """The decoded header."""

    remaining: bytes
    """Any remaining bytes in the buffer."""

    checksum_data: bytes
    """The bytes from the header that contribute to the checksum."""

    def assert_complete(self) -> None:
        """Assert that the buffer has been fully decoded.

        Raises:
            DecodeError if there are bytes remaining in the buffer.
        """
        if len(self.remaining) > 0:
            raise DecodeError(
                f"Buffer not fully decoded. Remaining bytes: {self.remaining.hex()}"
            )


class HeaderDecoder(Protocol[Hdr_co]):
    """Decoder for message headers."""

    @property
    def header_length(self) -> int:
        """Returns the length of the header in bytes."""

    def decode(self, buffer: bytes | bytearray) -> HeaderDecodeResult[Hdr_co]:
        """Decodes the header from the buffer.

        Returns the decoded header and any remaining bytes in the buffer.
        """


class MessageEncoder(Protocol[Hdr_contra, Msg_contra]):
    """Encoder for messages."""

    def size(self, message: Msg_contra) -> int:
        """Returns the size of the message in bytes."""

    def encode(self, header: Hdr_contra, message: Msg_contra) -> bytes:
        """Encodes the specified message into a sequence of bytes."""


@dataclass
class MessageDecodeResult(Generic[Msg_co]):
    """The result from a message decode operation.

    Includes fields to capture the decoded data and any remaining bytes that
    were not decoded.
    """

    message: Msg_co
    """The decoded message."""

    remaining: bytes
    """Any remaining bytes in the buffer."""

    def assert_complete(self) -> None:
        """Assert that the buffer has been fully decoded.

        Raises:
            DecodeError if there are bytes remaining in the buffer.
        """
        if len(self.remaining) > 0:
            raise DecodeError(
                f"Buffer not fully decoded. Remaining bytes: {self.remaining.hex()}"
            )


class MessageDecoder(Protocol[Hdr_contra, Msg_co]):
    """Decoder for messages."""

    def decode(
        self, buffer: bytes | bytearray, header: Hdr_contra
    ) -> MessageDecodeResult[Msg_co]:
        """Decodes a message from the buffer.

        Returns:
            The decoded message and any remaining bytes in the buffer.
        """


class HeaderFactory(Protocol[Hdr_co]):
    """A factory for creating headers."""

    def create_from_message(self, message: Message, message_length: int) -> Hdr_co:
        """Create a header for the specified message."""


@dataclass
class UnsupportedMessage(Message):
    """A dummy message.

    Used to unpack unsupported message types without throwing errors.
    """

    unsupported_id: int
    raw_data: bytes

    @override
    @property
    def message_id(self) -> int:
        return self.unsupported_id

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"UnsupportedMessage(message_id=0x{self.message_id:02x}, "
            f"raw_data=0x{self.raw_data.hex()})"
        )


class UnsupportedMessageDecoder(MessageDecoder[Hdr_contra, UnsupportedMessage]):
    """Default decoder implementation to handle unsupported messages."""

    @override
    def decode(
        self, buffer: bytes | bytearray, header: Hdr_contra
    ) -> MessageDecodeResult[UnsupportedMessage]:
        return MessageDecodeResult(
            message=UnsupportedMessage(
                unsupported_id=header.message_id,
                raw_data=buffer[: header.message_length],
            ),
            remaining=buffer[header.message_length :],
        )


class ChecksumCalculator(Protocol):
    """Defines the interface for a checksum calculator."""

    @property
    def checksum_length(self) -> int:
        """Returns the number of bytes in a checksum for this calculator."""

    def calculate(self, buffer: bytes | bytearray) -> bytes:
        """Calculates the checksum for the specified buffer."""

    def validate(self, buffer: bytes | bytearray, checksum: bytes | bytearray) -> bool:
        """Validates the specified buffer against the provided checksum."""


class MessageRegistry(Generic[Hdr]):
    """A registry of messages in an interface.

    Provides encoders and decoders for all messages in an interface.

    If a decoder has not been registered for a particular message, a dummy
    UnsupportedMessage decoder will be provided. This allows unsupported
    messages to be ignored while retaining the open socket connection.
    """

    def __init__(
        self,
        header_factory: HeaderFactory[Hdr],
        header_encoder: HeaderEncoder[Hdr],
        header_decoder: HeaderDecoder[Hdr],
        checksum_calculator: ChecksumCalculator,
    ) -> None:
        """Initialise the MessageRegistry."""
        self.header_factory = header_factory
        self.header_encoder = header_encoder
        self.header_decoder = header_decoder
        self.checksum_calculator = checksum_calculator

        self._unsupported_decoder: UnsupportedMessageDecoder[
            Hdr
        ] = UnsupportedMessageDecoder()

        self._encoder_map: dict[int, MessageEncoder[Hdr, Any]] = {}
        self._decoder_map: dict[int, MessageDecoder[Hdr, Message]] = {}

    def register(
        self,
        message_id: int,
        encoder: MessageEncoder[Hdr, Msg],
        decoder: MessageDecoder[Hdr, Msg],
    ) -> None:
        """Register a message in this message registry.

        If the message ID has already been registered the previusly registered
        encoder and decoder will be overwritten.
        """
        self._encoder_map[message_id] = encoder
        self._decoder_map[message_id] = decoder

    def get_encoder(self, message_id: int) -> MessageEncoder[Hdr, Any]:
        """Get an encoder for the specified message.

        Raises:
            NotImplementError if no encoder has been registered for the
                specified message ID.
        """
        encoder = self._encoder_map.get(message_id)
        if not encoder:
            raise NotImplementedError(
                f"Encoding of message 0x{message_id:02x} not implemented",
            )
        return encoder

    def get_decoder(self, message_id: int) -> MessageDecoder[Hdr, Message]:
        """Get a decoder for the specified message.

        If no decoder has been registered, the UnsupportedMessageDecoder is returned.
        """
        decoder = self._decoder_map.get(message_id)
        if not decoder:
            return self._unsupported_decoder
        return decoder


class DiscoveryRequest(Protocol):
    """Interface for AirTouch discovery requests.

    The discovery request directly returns the encoded bytes without an encoder
    because these are fixed byte string messages.
    """

    @property
    def data(self) -> bytes:
        """The encoded bytes of the discovery request."""


DiscoveryRequest_co = TypeVar(
    "DiscoveryRequest_co", bound=DiscoveryRequest, covariant=True
)


class DiscoveryResponse(Protocol):
    """A response from a discovery message."""

    @property
    def airtouch_id(self) -> str:
        """The ID of the discovered AirTouch system."""

    @property
    def host(self) -> str:
        """The host name or IP address of the discovered AirTouch system."""


TDiscoveryResponse = TypeVar("TDiscoveryResponse", bound=DiscoveryResponse)
TDiscoveryResponse_co = TypeVar(
    "TDiscoveryResponse_co", bound=DiscoveryResponse, covariant=True
)


class DiscoveryDecoder(Protocol, Generic[DiscoveryRequest_co, TDiscoveryResponse_co]):
    """Interface for decoding a discovery message."""

    def match(self, buffer: bytes | bytearray) -> bool:
        """Whether the buffer is a match for a supported message.

        Implementations should scan the minimum bytes necessary to identify
        whether the datagram buffer is decodeable.

        Args:
            buffer: all bytes from the received datagram.
        """

    def decode(
        self, buffer: bytes | bytearray
    ) -> DiscoveryRequest_co | TDiscoveryResponse_co:
        """Decode a message from the buffer.

        Args:
            buffer: all bytes from the received datagram.
        """


@dataclass(frozen=True)
class DiscoveryConfig(Generic[DiscoveryRequest_co, TDiscoveryResponse_co]):
    """Encapsulates configuration required to run discovery."""

    local_port: int
    """The local port number for receiving discovery responses."""
    remote_port: int
    """The remote port numbr for sending discovery request broadcasts."""

    request_factory: Callable[[], DiscoveryRequest_co]
    """Factory method to construct discovery requests."""

    response_type: type[TDiscoveryResponse_co]

    decoder: DiscoveryDecoder[DiscoveryRequest_co, TDiscoveryResponse_co]
    """Decoder for discovery responses."""
