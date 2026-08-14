"""Constants, enumerations and topic helpers for :mod:`pysillaprism`.

All topic strings are documented in the official *Prism MQTT* manual
(rel. 4.0, silla.industries). Values are published as plain UTF-8 strings on
the broker configured by the user; Prism acts purely as an MQTT client.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

#: Default MQTT base topic as shipped by Silla.
DEFAULT_BASE_TOPIC = "prism"

#: Charging-port number carried in per-port topics for a single-cable Prism.
#: DUO units expose port ``1`` (left cable) and ``2`` (right cable).
DEFAULT_PORT = 1

#: Special "port 0" used by the firmware for device-level topics such as
#: ``0/info/temperature/core``. It is not a charging port.
DEVICE_PORT = 0


class PortState(IntEnum):
    """Value of the ``<port>/state`` topic."""

    IDLE = 1
    """No vehicle connected."""
    WAITING = 2
    """Vehicle connected, waiting to charge."""
    CHARGING = 3
    """Vehicle charging."""
    PAUSE = 4
    """Charging paused."""


class PortError(IntEnum):
    """Value of the ``<port>/error`` topic.

    The MQTT manual only documents ``0``. The fault codes the firmware reports
    are not specified, so they are left as plain integers until Silla documents
    them or they are observed in the field.
    """

    NONE = 0
    """No error."""


class PortMode(IntEnum):
    """Value of the ``<port>/mode`` topic.

    Only :attr:`SOLAR`, :attr:`NORMAL` and :attr:`PAUSE` are user-settable via
    ``set_mode``. :attr:`AUTOLIMIT_PAUSE` is a read-only state the firmware
    reports when load balancing has suspended the session.
    """

    SOLAR = 1
    NORMAL = 2
    PAUSE = 3
    AUTOLIMIT_PAUSE = 7
    """Read-only: charging suspended by load balancing (insufficient power)."""


#: Modes that may be written back with ``set_mode``.
SETTABLE_MODES = (PortMode.SOLAR, PortMode.NORMAL, PortMode.PAUSE)


class CommandTopic(StrEnum):
    """Trailing segment of the ``<port>/command/<name>`` publish topics."""

    SET_MODE = "set_mode"
    SET_CURRENT_USER = "set_current_user"
    SET_CURRENT_LIMIT = "set_current_limit"
    ENABLE_NIGHT = "enable_night"
    DISABLE_NIGHT = "disable_night"
    SET_MODE_TRAPS = "set_mode_traps"


#: Payloads for the ``set_mode_traps`` command. Per the manual, ``-auth``
#: forwards the charge authorization and ``+auth`` de-authorizes it (the cable
#: must be connected and autostart disabled for it to take effect).
TRAPS_AUTHORIZE = "-auth"
TRAPS_DEAUTHORIZE = "+auth"

#: Value to publish to ``set_current_limit`` to effectively disable the limit
#: (the manual's documented "off" value).
CURRENT_LIMIT_OFF = 32.0


class InputEvent(StrEnum):
    """Kinds of momentary input events Prism reports under ``.../input``."""

    TOUCH = "touch"
    """Touch-button press sequence, e.g. ``"1,1,3"``."""
    KNOCK = "knock"
    """Knock on the cover, reported as a count of consecutive knocks."""


class CommandResult(StrEnum):
    """Outcome segment of ``commandresult/<command>/<result>``."""

    SUCCESS = "success"
    ERROR = "error"
