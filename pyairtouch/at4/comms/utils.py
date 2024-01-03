"""Common encoding and decoding utilities for the AirTouch 4 protocol."""


def encode_temperature(temperature: float) -> int:
    """Encode a temperature measurement value."""
    return (int(temperature * 10.0 + 500) << 5) & 0xFFE0


def decode_temperature(raw_value: int) -> float:
    """Decode a temperature measurement value."""
    return (((raw_value & 0xFFE0) >> 5) - 500) / 10.0
