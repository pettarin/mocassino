"""Tests for the actions and the button map.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.constants import Action, Button, ButtonPress, Mode
from mocassino.controller.actions import parse_button_map, resolve_button_map
from mocassino.controller.events import ButtonEvent
from mocassino.defaults import DEFAULT_BUTTON_MAP


class TestParseButtonMap:
    """Tests for the parse_button_map function"""

    def test_default(self):
        assert parse_button_map(DEFAULT_BUTTON_MAP) == {
            (Mode.MENU, ButtonEvent(Button.A)): Action.MENU_BACK,
            (Mode.MENU, ButtonEvent(Button.B)): Action.MENU_SELECT,
            (Mode.MENU, ButtonEvent(Button.X)): Action.MENU_UP,
            (Mode.MENU, ButtonEvent(Button.X, ButtonPress.LONG)): Action.MENU_SELECT,
            (Mode.MENU, ButtonEvent(Button.Y)): Action.MENU_DOWN,
            (Mode.MENU, ButtonEvent(Button.Y, ButtonPress.LONG)): Action.MENU_SELECT,
            (Mode.PLAYBACK, ButtonEvent(Button.A)): Action.PLAY_PAUSE,
            (Mode.PLAYBACK, ButtonEvent(Button.A, ButtonPress.LONG)): Action.OPEN_MENU,
            (Mode.PLAYBACK, ButtonEvent(Button.B)): Action.NEXT,
            (Mode.PLAYBACK, ButtonEvent(Button.B, ButtonPress.LONG)): Action.PREVIOUS,
            (Mode.PLAYBACK, ButtonEvent(Button.X)): Action.VOLUME_UP,
            (Mode.PLAYBACK, ButtonEvent(Button.X, ButtonPress.HOLD)): Action.SEEK_FORWARD,
            (Mode.PLAYBACK, ButtonEvent(Button.Y)): Action.VOLUME_DOWN,
            (Mode.PLAYBACK, ButtonEvent(Button.Y, ButtonPress.HOLD)): Action.SEEK_BACKWARD,
        }

    @pytest.mark.parametrize(
        "button_map",
        [
            {"settings": {"A": "next"}},
            {"menu": {"Q": "next"}},
            {"menu": {"A_short": "next"}},
            {"menu": {"A_": "next"}},
            {"menu": {"A_long_hold": "next"}},
            {"menu": {"A": "rewind"}},
        ],
    )
    def test_invalid(self, button_map):
        with pytest.raises(ValueError, match="is not a valid"):
            parse_button_map(button_map)


class TestResolveButtonMap:
    """Tests for the resolve_button_map function"""

    def test_default_is_not_shared(self):
        resolved = resolve_button_map({})
        assert resolved == DEFAULT_BUTTON_MAP
        resolved["menu"]["A"] = "next"
        assert DEFAULT_BUTTON_MAP["menu"]["A"] == "menu_back"

    @pytest.mark.parametrize(
        "overrides",
        [
            {"settings": {"A": "next"}},
            {"menu": {"Q": "next"}},
            {"menu": {"A": "rewind"}},
            {"menu": {"A": 5}},
        ],
    )
    def test_invalid_names(self, overrides):
        with pytest.raises(ValueError, match="is not a valid"):
            resolve_button_map(overrides)

    @pytest.mark.parametrize("overrides", ["menu", ["menu"], {"menu": "A"}, {"menu": None}])
    def test_invalid_shape(self, overrides):
        with pytest.raises(TypeError, match="expected a mapping"):
            resolve_button_map(overrides)

    def test_overrides(self):
        resolved = resolve_button_map(
            {"playback": {"B": "previous", "B_long": None, "X_long": "next", "Y_hold": None}}
        )
        assert resolved["menu"] == DEFAULT_BUTTON_MAP["menu"]
        assert resolved["playback"] == {
            "A": "play_pause",
            "A_long": "open_menu",
            "B": "previous",
            "X": "volume_up",
            "X_hold": "seek_forward",
            "X_long": "next",
            "Y": "volume_down",
        }
