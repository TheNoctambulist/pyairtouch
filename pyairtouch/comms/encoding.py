"""Common encoding/decoding utilities.

These utilities are independent of any specific interface.
"""

STRING_ENCODING = "utf-8"


def bool_to_bit(value: bool, offset: int) -> int:  # noqa: FBT001
    """Encode a boolean into a bit field.

    Returns:
        An integer with the bit at offset set to 1 if value is True, or 0 if
    value is False.
    """
    if value:
        return 1 << offset
    return 0


def bit_to_bool(value: int, offset: int) -> bool:
    """Decode a boolean from a bitfield.

    Returns:
        True if the bit at "offset" in "value" is 1, False otherwise.
    """
    mask = 1 << offset
    return (value & mask) == mask


def encode_c_string(value: str, length: int) -> bytes:
    """Encode a Python string into a fixed length null terminated string."""
    # Initialise a null filled byte array.
    buffer = bytearray(value, encoding=STRING_ENCODING)

    # Pad with nulls
    # This is safe even if the multiplier becomes negative (which will leave the
    # buffer unmodified).
    buffer.extend(b"\0" * (length - len(buffer)))

    # Truncate to the fixed length in case the value was too long.
    return buffer[:length]


def decode_c_string(value: bytes) -> str:
    """Decode a C-style null terminated string."""
    # Only keep the characters before the first null character
    return value.split(b"\0", 1)[0].decode(encoding=STRING_ENCODING)
