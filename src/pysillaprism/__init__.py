"""Transport-agnostic client library for the Silla Prism EV wallbox over MQTT.

Parses the Prism MQTT topics (rel. 4.0) into typed state and builds the
``command`` topics, without owning the MQTT connection — the caller wires it to
whatever client it already has (e.g. Home Assistant's ``mqtt`` integration).
"""

from __future__ import annotations

from .commands import (
    build_authorize,
    build_deauthorize,
    build_disable_night,
    build_enable_night,
    build_set_current_limit,
    build_set_current_user,
    build_set_mode,
)
from .const import (
    CURRENT_LIMIT_OFF,
    DEFAULT_BASE_TOPIC,
    DEFAULT_PORT,
    SETTABLE_MODES,
    CommandResult,
    InputEvent,
    PortMode,
    PortState,
)
from .device import PrismDevice
from .exceptions import PrismCommandError, PrismError, PrismParseError
from .models import (
    HelloInfo,
    PrismCommandResult,
    PrismEnergyData,
    PrismInputEvent,
    PrismPortStatus,
    PrismStatus,
)
from .parser import parse_hello, parse_input_values, parse_message

__all__ = [
    "CURRENT_LIMIT_OFF",
    "DEFAULT_BASE_TOPIC",
    "DEFAULT_PORT",
    "SETTABLE_MODES",
    "CommandResult",
    "HelloInfo",
    "InputEvent",
    "PortMode",
    "PortState",
    "PrismCommandError",
    "PrismCommandResult",
    "PrismDevice",
    "PrismEnergyData",
    "PrismError",
    "PrismInputEvent",
    "PrismParseError",
    "PrismPortStatus",
    "PrismStatus",
    "build_authorize",
    "build_deauthorize",
    "build_disable_night",
    "build_enable_night",
    "build_set_current_limit",
    "build_set_current_user",
    "build_set_mode",
    "parse_hello",
    "parse_input_values",
    "parse_message",
]

__version__ = "0.1.0"
