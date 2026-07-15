"""Builders for the Prism ``command`` topics.

Each function is pure: it validates its arguments and returns a
``(topic, payload)`` tuple ready to publish, without any I/O. This lets the
command surface be unit-tested and reused independently of a live broker.
"""

from __future__ import annotations

from .const import (
    SETTABLE_MODES,
    TRAPS_AUTHORIZE,
    TRAPS_DEAUTHORIZE,
    CommandTopic,
    PortMode,
)
from .exceptions import PrismCommandError

Command = tuple[str, str]


def _command_topic(base_topic: str, port: int, name: CommandTopic) -> str:
    return f"{base_topic}/{port}/command/{name.value}"


def build_set_mode(base_topic: str, port: int, mode: PortMode) -> Command:
    """Build a ``set_mode`` command. Only Solar/Normal/Pause are settable."""
    if mode not in SETTABLE_MODES:
        raise PrismCommandError(f"mode {mode!r} is not user-settable")
    return _command_topic(base_topic, port, CommandTopic.SET_MODE), str(int(mode))


def build_set_current_user(base_topic: str, port: int, amps: int) -> Command:
    """Build a ``set_current_user`` command (integer amps).

    This mirrors the +/- buttons on Prism's web UI; do not use it for dynamic
    modulation — use :func:`build_set_current_limit` for that.
    """
    if amps < 0:
        raise PrismCommandError(f"current must be non-negative, got {amps}")
    return _command_topic(base_topic, port, CommandTopic.SET_CURRENT_USER), str(int(amps))


def build_set_current_limit(base_topic: str, port: int, amps: float) -> Command:
    """Build a ``set_current_limit`` command (amps, one decimal).

    Intended for custom load-balancing logic. Set it to 32.0 A to disable the
    limit (see :data:`~pysillaprism.const.CURRENT_LIMIT_OFF`).
    """
    if amps < 0:
        raise PrismCommandError(f"current limit must be non-negative, got {amps}")
    return _command_topic(base_topic, port, CommandTopic.SET_CURRENT_LIMIT), f"{amps:.1f}"


def build_enable_night(base_topic: str, port: int) -> Command:
    """Build an ``enable_night`` command (enables the schedule set in the app)."""
    return _command_topic(base_topic, port, CommandTopic.ENABLE_NIGHT), ""


def build_disable_night(base_topic: str, port: int) -> Command:
    """Build a ``disable_night`` command."""
    return _command_topic(base_topic, port, CommandTopic.DISABLE_NIGHT), ""


def build_authorize(base_topic: str, port: int) -> Command:
    """Build the ``set_mode_traps`` command that authorizes charging."""
    return _command_topic(base_topic, port, CommandTopic.SET_MODE_TRAPS), TRAPS_AUTHORIZE


def build_deauthorize(base_topic: str, port: int) -> Command:
    """Build the ``set_mode_traps`` command that de-authorizes charging."""
    return _command_topic(base_topic, port, CommandTopic.SET_MODE_TRAPS), TRAPS_DEAUTHORIZE
