"""The actions, and the button map associating them to the button events.

A button map in plain form is what is stored in the configuration:
for each mode, the action of each button, with the "_long" suffix for the long presses
and the "_hold" suffix for the hold presses, which repeat while the button is held
(e.g., {"playback": {"A": "play_pause", "A_long": "open_menu", "X_hold": "seek_forward"}}).

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from mocassino.controller.events import Button, ButtonEvent, Press
from mocassino.model.state import Mode

type ButtonMap = dict[tuple[Mode, ButtonEvent], Action]

DEFAULT_BUTTON_MAP: dict[str, dict[str, str]] = {
    "menu": {
        "A": "menu_back",
        "B": "menu_select",
        "X": "menu_up",
        "X_long": "menu_select",
        "Y": "menu_down",
        "Y_long": "menu_select",
    },
    "playback": {
        "A": "play_pause",
        "A_long": "open_menu",
        "B": "next",
        "B_hold": "previous",
        "X": "volume_up",
        "X_hold": "seek_forward",
        "Y": "volume_down",
        "Y_hold": "seek_backward",
    },
}


class Action(StrEnum):
    """What a button event can ask for."""

    MENU_BACK = "menu_back"
    MENU_DOWN = "menu_down"
    MENU_SELECT = "menu_select"
    MENU_UP = "menu_up"
    NEXT = "next"
    OPEN_MENU = "open_menu"
    PLAY_PAUSE = "play_pause"
    PREVIOUS = "previous"
    SEEK_BACKWARD = "seek_backward"
    SEEK_FORWARD = "seek_forward"
    VOLUME_DOWN = "volume_down"
    VOLUME_UP = "volume_up"


def parse_button_map(button_map: Mapping[str, Mapping[str, str]]) -> ButtonMap:
    """Convert a button map from its plain form to the form used by the controller.

    :raises ValueError: if a mode, a button, a press, or an action is not valid
    """
    parsed: ButtonMap = {}
    for mode, actions in button_map.items():
        for key, action in actions.items():
            button, separator, suffix = key.partition("_")
            if separator and suffix not in (Press.HOLD, Press.LONG):
                raise ValueError(f"'{key}' is not a valid button press")
            event = ButtonEvent(Button(button), Press(suffix) if separator else Press.SHORT)
            parsed[(Mode(mode), event)] = Action(action)
    return parsed


def resolve_button_map(overrides: object) -> dict[str, dict[str, str]]:
    """Return the default button map, in plain form, changed by the given overrides.

    The overrides have the plain form too; they only need to list what differs
    from the default, and an action set to None leaves the button without action.

    :raises TypeError: if the overrides do not have the plain form
    :raises ValueError: if a mode, a button, or an action is not valid
    """
    if not isinstance(overrides, Mapping):
        raise TypeError("expected a mapping of modes")
    resolved = {mode: dict(actions) for mode, actions in DEFAULT_BUTTON_MAP.items()}
    for mode, actions in overrides.items():
        if not isinstance(actions, Mapping):
            raise TypeError(f"expected a mapping of buttons for '{mode}'")
        for key, action in actions.items():
            if action is None:
                resolved.setdefault(str(mode), {}).pop(str(key), None)
            else:
                resolved.setdefault(str(mode), {})[str(key)] = str(action)
    parse_button_map(resolved)
    return resolved
