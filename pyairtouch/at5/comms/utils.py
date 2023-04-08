"""Common encoding and decoding utilities for the AirTouch 5 protocol."""


def encode_set_point(set_point: float) -> int:
    """Encode a set-point temperature."""
    return int(set_point * 10.0 - 100)


def decode_set_point(raw_value: int) -> float:
    """Decode a set-point temperature."""
    return (raw_value + 100) / 10.0


def encode_temperature(temperature: float) -> int:
    """Encode a temperature measurement value."""
    return int(temperature * 10.0 + 500)


def decode_temperature(raw_value: int) -> float:
    """Decode a temperature measurement value."""
    return (raw_value - 500) / 10.0
