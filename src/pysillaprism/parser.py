"""Pure parsing of incoming Prism MQTT messages.

:func:`parse_message` maps a raw ``(topic, payload)`` pair to one of the
:data:`ParsedMessage` variants, or ``None`` when the topic does not belong to
this device or is not recognised. It never mutates state and never performs
I/O, which keeps it trivially unit-testable against captured payloads.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .const import (
    CommandResult,
    InputEvent,
    PortMode,
    PortState,
)
from .exceptions import PrismParseError
from .models import HelloInfo, PrismCommandResult, PrismInputEvent


@dataclass(frozen=True, slots=True)
class StatusUpdate:
    """Assignment of a parsed value to a status attribute.

    ``target`` selects where the value belongs: ``"port"`` (with ``port`` set),
    ``"energy"`` for the device power flows, or ``"device"`` for top-level
    fields such as the core temperature.
    """

    target: str
    field: str
    value: object
    port: int | None = None


@dataclass(frozen=True, slots=True)
class HelloUpdate:
    """A parsed ``hello`` announcement."""

    info: HelloInfo


@dataclass(frozen=True, slots=True)
class EventMessage:
    """A momentary input event (touch/knock)."""

    event: PrismInputEvent


@dataclass(frozen=True, slots=True)
class CommandResultMessage:
    """A command acknowledgement."""

    result: PrismCommandResult


ParsedMessage = StatusUpdate | HelloUpdate | EventMessage | CommandResultMessage


def _to_float(payload: str) -> float:
    try:
        return float(payload)
    except ValueError as err:
        raise PrismParseError(f"expected a number, got {payload!r}") from err


def _to_int(payload: str) -> int:
    # Tolerate integer values published with a trailing ".0".
    try:
        return int(float(payload))
    except ValueError as err:
        raise PrismParseError(f"expected an integer, got {payload!r}") from err


def _to_state(payload: str) -> PortState:
    try:
        return PortState(_to_int(payload))
    except ValueError as err:
        raise PrismParseError(f"unknown port state {payload!r}") from err


def _to_mode(payload: str) -> PortMode:
    try:
        return PortMode(_to_int(payload))
    except ValueError as err:
        raise PrismParseError(f"unknown port mode {payload!r}") from err


#: Per-port single-segment topics: firmware name -> (status attribute, coercer).
_PORT_FIELDS: dict[str, tuple[str, Callable[[str], object]]] = {
    "state": ("state", _to_state),
    "mode": ("mode", _to_mode),
    "volt": ("voltage", _to_float),
    "w": ("power", _to_float),
    "amp": ("current", _to_int),
    "pilot": ("pilot", _to_float),
    "user_amp": ("user_current", _to_int),
    "session_time": ("session_time", _to_int),
    "wh": ("session_energy", _to_float),
    "wh_total": ("total_energy", _to_float),
    "error": ("error", _to_int),
}

#: ``energy_data/<name>`` topics -> status attribute on :class:`PrismEnergyData`.
_ENERGY_FIELDS = {
    "power_grid": "power_grid",
    "power_solar": "power_solar",
    "power_house": "power_house",
}

_HELLO_RE = re.compile(
    r"^(?P<serial>\S+)"
    r"(?:\s+(?P<sw>\S+))?"
    r"(?:\s+\(evsemd\s+v?(?P<evsemd>[^)]+)\))?",
)


def parse_hello(payload: str) -> HelloInfo:
    """Parse a ``hello`` payload such as ``"Prism-A00006 3.2.77 (evsemd v1.1.1)"``."""
    match = _HELLO_RE.match(payload.strip())
    if not match or not match.group("serial"):
        raise PrismParseError(f"unrecognised hello payload {payload!r}")
    return HelloInfo(
        serial=match.group("serial"),
        sw_version=match.group("sw"),
        evsemd_version=match.group("evsemd"),
        raw=payload,
    )


def parse_input_values(payload: str) -> tuple[int, ...]:
    """Parse a touch/knock payload (``"1,1,3"`` or ``"3"``) into integers."""
    payload = payload.strip()
    if not payload:
        return ()
    try:
        return tuple(int(part) for part in payload.split(","))
    except ValueError as err:
        raise PrismParseError(f"unrecognised input payload {payload!r}") from err


def strip_base(base_topic: str, topic: str) -> str | None:
    """Return ``topic`` with the ``base_topic/`` prefix removed, else ``None``."""
    prefix = f"{base_topic}/"
    if not topic.startswith(prefix):
        return None
    return topic[len(prefix) :]


def parse_message(base_topic: str, topic: str, payload: str) -> ParsedMessage | None:
    """Classify and parse one MQTT message.

    Returns ``None`` for topics outside ``base_topic`` or not understood.
    Raises :class:`~pysillaprism.exceptions.PrismParseError` for a recognised
    topic carrying a malformed payload.
    """
    remainder = strip_base(base_topic, topic)
    if remainder is None:
        return None
    segments = remainder.split("/")

    # prism/hello
    if segments == ["hello"]:
        return HelloUpdate(parse_hello(payload))

    # prism/energy_data/<name>
    if segments[0] == "energy_data" and len(segments) == 2:
        attr = _ENERGY_FIELDS.get(segments[1])
        if attr is None:
            return None
        return StatusUpdate(target="energy", field=attr, value=_to_float(payload))

    # prism/commandresult/<command>/<result>
    if segments[0] == "commandresult" and len(segments) == 3:
        try:
            result = CommandResult(segments[2])
        except ValueError:
            return None
        return CommandResultMessage(
            PrismCommandResult(command=segments[1], result=result, message=payload)
        )

    # Everything else is port-scoped: prism/<port>/...
    if not segments[0].isdigit():
        return None
    port = int(segments[0])
    rest = segments[1:]

    # prism/0/info/temperature/core  (device-level)
    if rest == ["info", "temperature", "core"]:
        return StatusUpdate(target="device", field="temperature", value=_to_float(payload))

    # prism/<port>/input/<kind>
    if len(rest) == 2 and rest[0] == "input":
        try:
            kind = InputEvent(rest[1])
        except ValueError:
            return None
        return EventMessage(
            PrismInputEvent(
                port=port,
                kind=kind,
                raw=payload,
                values=parse_input_values(payload),
            )
        )

    # prism/<port>/<field>  (status)
    if len(rest) == 1:
        mapping = _PORT_FIELDS.get(rest[0])
        if mapping is None:
            return None
        attr, coerce = mapping
        return StatusUpdate(target="port", field=attr, value=coerce(payload), port=port)

    # prism/<port>/command/...  are our own outbound topics; ignore inbound.
    return None
