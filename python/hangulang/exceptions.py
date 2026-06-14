class HangulangError(Exception):
    """Base class for hangulang-python errors."""


class UnsupportedFormatError(HangulangError):
    """Raised when the input format is not supported by the conversion engine."""


class ParseError(HangulangError):
    """Raised when the input cannot be read or parsed."""


class ConversionError(HangulangError):
    """Raised when conversion fails after input handling succeeds."""

