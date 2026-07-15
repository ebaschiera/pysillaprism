"""Tests for the pure command builders."""

from __future__ import annotations

import pytest

from pysillaprism import (
    PortMode,
    PrismCommandError,
    build_authorize,
    build_deauthorize,
    build_disable_night,
    build_enable_night,
    build_set_current_limit,
    build_set_current_user,
    build_set_mode,
)

BASE = "prism"


def test_set_mode_normal():
    assert build_set_mode(BASE, 1, PortMode.NORMAL) == ("prism/1/command/set_mode", "2")


def test_set_mode_solar_on_second_port():
    assert build_set_mode(BASE, 2, PortMode.SOLAR) == ("prism/2/command/set_mode", "1")


def test_set_mode_rejects_autolimit():
    with pytest.raises(PrismCommandError):
        build_set_mode(BASE, 1, PortMode.AUTOLIMIT_PAUSE)


def test_set_current_user_is_integer():
    assert build_set_current_user(BASE, 1, 16) == ("prism/1/command/set_current_user", "16")


def test_set_current_user_rejects_negative():
    with pytest.raises(PrismCommandError):
        build_set_current_user(BASE, 1, -1)


def test_set_current_limit_one_decimal():
    assert build_set_current_limit(BASE, 1, 9.6) == ("prism/1/command/set_current_limit", "9.6")
    assert build_set_current_limit(BASE, 1, 32) == ("prism/1/command/set_current_limit", "32.0")


def test_night_commands():
    assert build_enable_night(BASE, 1) == ("prism/1/command/enable_night", "")
    assert build_disable_night(BASE, 1) == ("prism/1/command/disable_night", "")


def test_authorize_payloads():
    assert build_authorize(BASE, 1) == ("prism/1/command/set_mode_traps", "-auth")
    assert build_deauthorize(BASE, 1) == ("prism/1/command/set_mode_traps", "+auth")
