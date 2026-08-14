"""Parser tests driven by payloads captured from a live Prism Solar (fw 3.x)."""

from __future__ import annotations

import pytest

from pysillaprism import (
    CommandResult,
    InputEvent,
    PortError,
    PortMode,
    PortState,
    PrismParseError,
    parse_hello,
    parse_input_values,
    parse_message,
)
from pysillaprism.parser import (
    CommandResultMessage,
    EventMessage,
    HelloUpdate,
    StatusUpdate,
)

BASE = "prism"

# Retained state topics exactly as observed on the broker.
REAL_STATUS = [
    ("prism/1/state", "1", "port", "state", PortState.IDLE, 1),
    ("prism/1/amp", "0", "port", "current", 0, 1),
    ("prism/1/wh", "3900", "port", "session_energy", 3900.0, 1),
    ("prism/1/pilot", "6.0", "port", "pilot", 6.0, 1),
    ("prism/1/user_amp", "6", "port", "user_current", 6, 1),
    ("prism/1/volt", "236.0", "port", "voltage", 236.0, 1),
    ("prism/1/w", "0", "port", "power", 0.0, 1),
    ("prism/1/wh_total", "719800", "port", "total_energy", 719800.0, 1),
    ("prism/1/error", "0", "port", "error", PortError.NONE, 1),
    ("prism/1/mode", "2", "port", "mode", PortMode.NORMAL, 1),
    ("prism/1/session_time", "16030", "port", "session_time", 16030, 1),
    ("prism/energy_data/power_grid", "3", "energy", "power_grid", 3.0, None),
    ("prism/energy_data/power_solar", "0", "energy", "power_solar", 0.0, None),
    ("prism/energy_data/power_house", "0", "energy", "power_house", 0.0, None),
    ("prism/0/info/temperature/core", "35", "device", "temperature", 35.0, None),
]


@pytest.mark.parametrize("topic,payload,target,field,value,port", REAL_STATUS)
def test_real_status_topics(topic, payload, target, field, value, port):
    parsed = parse_message(BASE, topic, payload)
    assert isinstance(parsed, StatusUpdate)
    assert parsed.target == target
    assert parsed.field == field
    assert parsed.value == value
    assert parsed.port == port


def test_negative_power_grid_export():
    parsed = parse_message(BASE, "prism/energy_data/power_grid", "-2")
    assert isinstance(parsed, StatusUpdate)
    assert parsed.value == -2.0


def test_state_and_mode_are_enum_members():
    state = parse_message(BASE, "prism/1/state", "3")
    mode = parse_message(BASE, "prism/1/mode", "7")
    assert isinstance(state, StatusUpdate) and state.value is PortState.CHARGING
    assert isinstance(mode, StatusUpdate) and mode.value is PortMode.AUTOLIMIT_PAUSE


def test_hello_full():
    parsed = parse_message(BASE, "prism/hello", "Prism-A00006 3.2.77 (evsemd v1.1.1)")
    assert isinstance(parsed, HelloUpdate)
    assert parsed.info.serial == "Prism-A00006"
    assert parsed.info.sw_version == "3.2.77"
    assert parsed.info.evsemd_version == "1.1.1"


def test_hello_v1_style():
    info = parse_hello("Cartender-Prism 1.4 (evsemd v1.0.0)")
    assert info.serial == "Cartender-Prism"
    assert info.sw_version == "1.4"
    assert info.evsemd_version == "1.0.0"


def test_hello_serial_only():
    info = parse_hello("Prism-A00006")
    assert info.serial == "Prism-A00006"
    assert info.sw_version is None
    assert info.evsemd_version is None


def test_command_result_success():
    parsed = parse_message(BASE, "prism/commandresult/set_mode/success", "")
    assert isinstance(parsed, CommandResultMessage)
    assert parsed.result.command == "set_mode"
    assert parsed.result.result is CommandResult.SUCCESS
    assert parsed.result.message == ""


def test_command_result_error_carries_message():
    parsed = parse_message(
        BASE, "prism/commandresult/set_mode/error", "Bad syntax, mode must be [0-9]"
    )
    assert isinstance(parsed, CommandResultMessage)
    assert parsed.result.result is CommandResult.ERROR
    assert "Bad syntax" in parsed.result.message


@pytest.mark.parametrize(
    "payload,expected",
    [("1", (1,)), ("1,1,1", (1, 1, 1)), ("3", (3,)), ("1,1,3", (1, 1, 3))],
)
def test_touch_event(payload, expected):
    parsed = parse_message(BASE, "prism/1/input/touch", payload)
    assert isinstance(parsed, EventMessage)
    assert parsed.event.kind is InputEvent.TOUCH
    assert parsed.event.port == 1
    assert parsed.event.values == expected
    assert parsed.event.raw == payload


def test_knock_event():
    parsed = parse_message(BASE, "prism/0/input/knock", "3")
    assert isinstance(parsed, EventMessage)
    assert parsed.event.kind is InputEvent.KNOCK
    assert parsed.event.values == (3,)


def test_parse_input_values_empty():
    assert parse_input_values("") == ()


def test_custom_base_topic():
    assert parse_message("garage/prism", "garage/prism/1/state", "1") is not None
    assert parse_message("garage/prism", "prism/1/state", "1") is None


def test_topic_outside_base_returns_none():
    assert parse_message(BASE, "zigbee2mqtt/foo", "1") is None


def test_outbound_command_topic_is_ignored():
    assert parse_message(BASE, "prism/1/command/set_mode", "2") is None


def test_unknown_field_returns_none():
    assert parse_message(BASE, "prism/1/unknownfield", "42") is None


def test_malformed_number_raises():
    with pytest.raises(PrismParseError):
        parse_message(BASE, "prism/1/volt", "not-a-number")


def test_unknown_state_value_raises():
    with pytest.raises(PrismParseError):
        parse_message(BASE, "prism/1/state", "99")


def test_undocumented_error_code_is_kept_as_int():
    parsed = parse_message(BASE, "prism/1/error", "12")
    assert isinstance(parsed, StatusUpdate)
    assert parsed.value == 12
    assert not isinstance(parsed.value, PortError)
