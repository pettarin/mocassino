"""The button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from dataclasses import dataclass
from enum import StrEnum


class Button(StrEnum):
    """The four buttons of the Pirate Audio hat.

    A is top-left, B is bottom-left, X is top-right, and Y is bottom-right.
    """

    A = "A"
    B = "B"
    X = "X"
    Y = "Y"


class Press(StrEnum):
    """The kinds of press of a button.

    A button released early gives one short press.
    A button held gives one long press, as soon as it has been held long enough,
    and a hold press at the same time and then repeatedly, until it is released.

    Defined before the button event, as the latter refers to it.
    """

    HOLD = "hold"
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class ButtonEvent:
    """A press of a button, of a given kind."""

    button: Button
    press: Press = Press.SHORT
