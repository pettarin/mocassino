"""The button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

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


# The buttons in the order they are met going clockwise around the display, from the top-left
BUTTONS_CLOCKWISE: tuple[Button, ...] = (Button.A, Button.X, Button.Y, Button.B)


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

    def rotated(self, orientation: int) -> ButtonEvent:
        """Return this event as if pressed on the button taking the place of its button.

        When what is shown on the display is rotated clockwise by the given degrees,
        each corner of it ends up next to another button: the buttons are then taken for
        those that were next to what is shown now next to them, so that, for who looks at
        the display the right way up, the button at each corner keeps doing the same thing.

        :param orientation: 0, 90, 180, or 270 degrees
        """
        index = BUTTONS_CLOCKWISE.index(self.button) - orientation // 90
        return ButtonEvent(BUTTONS_CLOCKWISE[index % len(BUTTONS_CLOCKWISE)], self.press)
