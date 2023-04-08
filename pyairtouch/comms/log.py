"""Logging extensions for pyairtouch communications."""

import logging
from typing import TYPE_CHECKING, Any

from typing_extensions import override

# Work-around for type checking in Python before v3.11.
# See: https://github.com/python/typeshed/issues/7855
if TYPE_CHECKING:
    _LoggerAdapter = logging.LoggerAdapter[logging.Logger]
else:
    _LoggerAdapter = logging.LoggerAdapter


class CommsLogger(_LoggerAdapter):
    """Adapts logging.Logger with support for formatting byte strings."""

    def __init__(self, delegate: logging.Logger) -> None:
        """Initialise the CommsLogger wrapping a delegate Logger."""
        super().__init__(delegate)

    @override
    def log(
        self,
        level: int,
        msg: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if self.isEnabledFor(level):
            # Replace any "bytes" or "bytearray" objects with a nicely formatted
            # hex string
            updated_args = list(args)
            for i in range(len(args)):
                match args[i]:
                    case bytes() | bytearray() as arg:
                        updated_args[i] = arg.hex(sep=" ", bytes_per_sep=1)
            self.logger.log(level, msg, *updated_args, **kwargs)


def getLogger(name: str | None = None) -> CommsLogger:  # noqa: N802 name as per logging module
    """Convenience constructor for a CommsLogger."""
    return CommsLogger(logging.getLogger(name))
