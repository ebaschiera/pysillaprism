"""Stateful Prism device: state accumulation plus a command surface.

:class:`PrismDevice` is transport-agnostic. It does not open an MQTT
connection; the caller feeds it inbound messages via :meth:`handle_message`
and supplies a ``publish`` callback that :class:`PrismDevice` invokes to send
commands. The callback may be synchronous or return an awaitable, so it maps
cleanly onto Home Assistant's ``mqtt.async_publish`` as well as plain clients.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from . import commands
from .const import DEFAULT_BASE_TOPIC, DEFAULT_PORT, PortMode
from .exceptions import PrismError, PrismParseError
from .models import (
    HelloInfo,
    PrismCommandResult,
    PrismInputEvent,
    PrismStatus,
)
from .parser import (
    CommandResultMessage,
    EventMessage,
    HelloUpdate,
    ParsedMessage,
    StatusUpdate,
    parse_message,
)

_LOGGER = logging.getLogger(__name__)

PublishCallback: TypeAlias = Callable[[str, str], Awaitable[None] | None]


class PrismDevice:
    """A single Prism wallbox addressed by its MQTT base topic."""

    def __init__(
        self,
        base_topic: str = DEFAULT_BASE_TOPIC,
        *,
        publish: PublishCallback | None = None,
    ) -> None:
        self.base_topic = base_topic
        self.status = PrismStatus(base_topic=base_topic)
        self._publish = publish

        #: Called after any accumulated-status change.
        self.on_status_update: Callable[[StatusUpdate], None] | None = None
        #: Called for each touch/knock input event.
        self.on_event: Callable[[PrismInputEvent], None] | None = None
        #: Called for each command acknowledgement.
        self.on_command_result: Callable[[PrismCommandResult], None] | None = None
        #: Called when a ``hello`` announcement is received.
        self.on_hello: Callable[[HelloInfo], None] | None = None

    @property
    def subscription_topic(self) -> str:
        """Wildcard topic covering every message from this device."""
        return f"{self.base_topic}/#"

    # -- inbound ---------------------------------------------------------

    def handle_message(self, topic: str, payload: str) -> ParsedMessage | None:
        """Process one inbound MQTT message, updating state and firing callbacks.

        Malformed payloads on known topics are logged and dropped, keeping the
        last known good value. Returns the parsed message, or ``None`` when the
        topic is irrelevant or unparseable.
        """
        try:
            parsed = parse_message(self.base_topic, topic, payload)
        except PrismParseError as err:
            _LOGGER.debug("Ignoring %s=%r: %s", topic, payload, err)
            return None
        if parsed is None:
            return None

        match parsed:
            case StatusUpdate():
                self._apply_status(parsed)
                if self.on_status_update is not None:
                    self.on_status_update(parsed)
            case HelloUpdate():
                self.status.hello = parsed.info
                if self.on_hello is not None:
                    self.on_hello(parsed.info)
            case EventMessage():
                if self.on_event is not None:
                    self.on_event(parsed.event)
            case CommandResultMessage():
                if self.on_command_result is not None:
                    self.on_command_result(parsed.result)
        return parsed

    def _apply_status(self, update: StatusUpdate) -> None:
        if update.target == "port":
            assert update.port is not None
            setattr(self.status.port(update.port), update.field, update.value)
        elif update.target == "energy":
            setattr(self.status.energy, update.field, update.value)
        elif update.target == "device":
            setattr(self.status, update.field, update.value)

    # -- outbound --------------------------------------------------------

    async def _send(self, command: commands.Command) -> None:
        if self._publish is None:
            raise PrismError("no publish callback configured")
        topic, payload = command
        result = self._publish(topic, payload)
        if inspect.isawaitable(result):
            await result

    async def set_mode(self, mode: PortMode, port: int = DEFAULT_PORT) -> None:
        """Set the operating mode (Solar/Normal/Pause) of ``port``."""
        await self._send(commands.build_set_mode(self.base_topic, port, mode))

    async def set_current_user(self, amps: int, port: int = DEFAULT_PORT) -> None:
        """Set the user maximum charging current, in integer amps."""
        await self._send(commands.build_set_current_user(self.base_topic, port, amps))

    async def set_current_limit(self, amps: float, port: int = DEFAULT_PORT) -> None:
        """Set the charging current limit (for load-balancing), in amps."""
        await self._send(commands.build_set_current_limit(self.base_topic, port, amps))

    async def enable_night(self, port: int = DEFAULT_PORT) -> None:
        """Enable the night schedule configured in the Silla app."""
        await self._send(commands.build_enable_night(self.base_topic, port))

    async def disable_night(self, port: int = DEFAULT_PORT) -> None:
        """Disable the night schedule."""
        await self._send(commands.build_disable_night(self.base_topic, port))

    async def authorize(self, port: int = DEFAULT_PORT) -> None:
        """Authorize charging (cable connected, autostart disabled)."""
        await self._send(commands.build_authorize(self.base_topic, port))

    async def deauthorize(self, port: int = DEFAULT_PORT) -> None:
        """De-authorize charging."""
        await self._send(commands.build_deauthorize(self.base_topic, port))
