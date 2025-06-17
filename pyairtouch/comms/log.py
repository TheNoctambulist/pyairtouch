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


class LogEvent:
    """A latching log event that will log only once until the event is withdrawn."""

    def __init__(self, logger: logging.Logger, log_level: int) -> None:
        """Initialise the LogEvent."""
        self.logger = logger
        self.log_level = log_level
        self._event_logged = False

    def log(self, msg: Any, *args: Any) -> None:  # noqa: ANN401
        """Log the event.

        If this is the first occurence of the event it will be logged at the
        defined level, otherwise logging will be at debug level only.
        """
        level = logging.DEBUG
        if not self._event_logged:
            level = self.log_level
            self._event_logged = True

        self.logger.log(level, msg, *args)

    def withdraw(self, msg: Any = None, *args: Any) -> None:  # noqa: ANN401
        """Mark this event as withdrawn.

        An optional message can be provided to highlight in the log that a
        recurring event is no longer occurring.
        """
        if self._event_logged and msg is not None:
            self.logger.log(self.log_level, msg, *args)
        self._event_logged = False
