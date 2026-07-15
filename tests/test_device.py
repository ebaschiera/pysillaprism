"""Tests for the stateful PrismDevice, incl. sync/async publish callbacks."""

from __future__ import annotations

import pytest

from pysillaprism import (
    PortMode,
    PortState,
    PrismCommandResult,
    PrismDevice,
    PrismError,
    PrismInputEvent,
)

# The exact retained burst captured from the live wallbox on connect.
RETAINED_BURST = [
    ("prism/1/state", "1"),
    ("prism/1/amp", "0"),
    ("prism/1/wh", "3900"),
    ("prism/1/pilot", "6.0"),
    ("prism/1/user_amp", "6"),
    ("prism/1/volt", "236.0"),
    ("prism/1/w", "0"),
    ("prism/1/wh_total", "719800"),
    ("prism/1/error", "0"),
    ("prism/1/mode", "2"),
    ("prism/0/info/temperature/core", "35"),
    ("prism/energy_data/power_grid", "0"),
    ("prism/energy_data/power_solar", "0"),
    ("prism/energy_data/power_house", "0"),
]


def test_accumulates_retained_burst():
    device = PrismDevice("prism")
    for topic, payload in RETAINED_BURST:
        device.handle_message(topic, payload)

    port = device.status.port(1)
    assert port.state is PortState.IDLE
    assert port.mode is PortMode.NORMAL
    assert port.voltage == 236.0
    assert port.user_current == 6
    assert port.total_energy == 719800.0
    assert device.status.temperature == 35.0
    assert device.status.energy.power_grid == 0.0


def test_subscription_topic():
    assert PrismDevice("prism").subscription_topic == "prism/#"
    assert PrismDevice("garage/prism").subscription_topic == "garage/prism/#"


def test_partial_updates_keep_previous_values():
    device = PrismDevice("prism")
    device.handle_message("prism/1/volt", "236.0")
    device.handle_message("prism/1/volt", "233.5")
    assert device.status.port(1).voltage == 233.5
    assert device.status.port(1).state is None  # never reported


def test_malformed_payload_keeps_last_good():
    device = PrismDevice("prism")
    device.handle_message("prism/1/volt", "236.0")
    device.handle_message("prism/1/volt", "garbage")
    assert device.status.port(1).voltage == 236.0


def test_status_update_callback_fires():
    device = PrismDevice("prism")
    seen: list[str] = []
    device.on_status_update = lambda upd: seen.append(upd.field)
    device.handle_message("prism/1/state", "3")
    assert seen == ["state"]


def test_hello_updates_device_info_and_callback():
    device = PrismDevice("prism")
    captured = []
    device.on_hello = captured.append
    device.handle_message("prism/hello", "Prism-A00006 3.2.77 (evsemd v1.1.1)")
    assert device.status.hello is not None
    assert device.status.hello.serial == "Prism-A00006"
    assert captured[0].sw_version == "3.2.77"


def test_event_and_command_result_callbacks():
    device = PrismDevice("prism")
    events: list[PrismInputEvent] = []
    results: list[PrismCommandResult] = []
    device.on_event = events.append
    device.on_command_result = results.append

    device.handle_message("prism/1/input/touch", "1,1,3")
    device.handle_message("prism/commandresult/set_mode/success", "")

    assert events[0].values == (1, 1, 3)
    assert results[0].command == "set_mode"


async def test_async_publish_callback():
    published: list[tuple[str, str]] = []

    async def publish(topic: str, payload: str) -> None:
        published.append((topic, payload))

    device = PrismDevice("prism", publish=publish)
    await device.set_mode(PortMode.NORMAL)
    await device.set_current_limit(9.6)
    await device.authorize()

    assert published == [
        ("prism/1/command/set_mode", "2"),
        ("prism/1/command/set_current_limit", "9.6"),
        ("prism/1/command/set_mode_traps", "-auth"),
    ]


async def test_sync_publish_callback():
    published: list[tuple[str, str]] = []
    device = PrismDevice("prism", publish=lambda t, p: published.append((t, p)))
    await device.set_current_user(16)
    assert published == [("prism/1/command/set_current_user", "16")]


async def test_command_without_publish_raises():
    device = PrismDevice("prism")
    with pytest.raises(PrismError):
        await device.set_mode(PortMode.PAUSE)
