"""Common encoding/decoding utilities.

These utilities are independent of any specific interface.
"""


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


def decode_c_string(value: bytes) -> str:
    """Decode a C-style null terminated string."""
    # Only keep the characters before the first null character
    return value.split(b"\0", 1)[0].decode()
