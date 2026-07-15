"""Data models for :mod:`pysillaprism`.

The status objects accumulate state: Prism only publishes a topic when its
value changes, so a field stays ``None`` until the firmware has reported it at
least once. Events (touch, knock, command results) are momentary and delivered
through callbacks rather than stored on the status.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .const import CommandResult, InputEvent, PortMode, PortState


@dataclass(slots=True)
class PrismPortStatus:
    """Live status of a single charging port.

    Units follow the Prism MQTT manual: ``current`` is in milliamps (as
    published by the firmware for compatibility), everything else in the SI
    unit named by the attribute.
    """

    port: int
    #: ``state`` topic — presence/charging state of the port.
    state: PortState | None = None
    #: ``mode`` topic — current operating mode.
    mode: PortMode | None = None
    #: ``volt`` topic, in volts.
    voltage: float | None = None
    #: ``w`` topic, in watts.
    power: float | None = None
    #: ``amp`` topic, in milliamps.
    current: int | None = None
    #: ``pilot`` topic — current signalled to the car, in amps.
    pilot: float | None = None
    #: ``user_amp`` topic — user-set maximum current, in amps.
    user_current: int | None = None
    #: ``session_time`` topic, in seconds.
    session_time: int | None = None
    #: ``wh`` topic — energy delivered this session, in watt-hours.
    session_energy: float | None = None
    #: ``wh_total`` topic — lifetime energy delivered, in watt-hours.
    total_energy: float | None = None
    #: ``error`` topic — port error code (``0`` means no error).
    error: int | None = None


@dataclass(slots=True)
class PrismEnergyData:
    """Device-level power flows from the ``energy_data`` topics.

    ``power_solar`` and ``power_house`` are only meaningful when a Powerwall/
    meter is configured; otherwise the firmware publishes ``0``.
    """

    #: ``energy_data/power_grid``, in watts. Positive = import, negative =
    #: export.
    power_grid: float | None = None
    #: ``energy_data/power_solar``, in watts.
    power_solar: float | None = None
    #: ``energy_data/power_house``, in watts.
    power_house: float | None = None


@dataclass(frozen=True, slots=True)
class HelloInfo:
    """Parsed ``hello`` announcement, sent by Prism when it (re)connects.

    Example payload: ``"Prism-A00006 3.2.77 (evsemd v1.1.1)"``.
    """

    serial: str
    sw_version: str | None
    evsemd_version: str | None
    raw: str


@dataclass(slots=True)
class PrismStatus:
    """Complete accumulated status of a Prism device."""

    base_topic: str
    ports: dict[int, PrismPortStatus] = field(default_factory=dict)
    energy: PrismEnergyData = field(default_factory=PrismEnergyData)
    #: Device core temperature (``0/info/temperature/core``), in °C.
    temperature: float | None = None
    #: Last ``hello`` seen, if any. Populated opportunistically on reconnect.
    hello: HelloInfo | None = None

    def port(self, number: int) -> PrismPortStatus:
        """Return the status for ``number``, creating it on first access."""
        status = self.ports.get(number)
        if status is None:
            status = PrismPortStatus(port=number)
            self.ports[number] = status
        return status


@dataclass(frozen=True, slots=True)
class PrismInputEvent:
    """A momentary input event (touch sequence or knock)."""

    port: int
    kind: InputEvent
    raw: str
    #: Parsed integer sequence, e.g. ``(1, 1, 3)`` for a ``"1,1,3"`` touch.
    values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PrismCommandResult:
    """Outcome reported on ``commandresult/<command>/<result>``."""

    command: str
    result: CommandResult
    #: Empty on success; the firmware's error description on failure.
    message: str
