"""Exceptions raised by :mod:`pysillaprism`."""

from __future__ import annotations


class PrismError(Exception):
    """Base class for all pysillaprism errors."""


class PrismCommandError(PrismError):
    """Raised when a command cannot be built (e.g. an out-of-range value)."""


class PrismParseError(PrismError):
    """Raised when a payload cannot be parsed into its expected type."""
