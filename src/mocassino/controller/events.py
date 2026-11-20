"""The button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

from dataclasses import dataclass

from mocassino.constants import Button, ButtonPress

# The buttons in the order they are met going clockwise around the display, from the top-left
BUTTONS_CLOCKWISE: tuple[Button, ...] = (Button.A, Button.X, Button.Y, Button.B)


@dataclass(frozen=True)
class ButtonEvent:
    """A press of a button, of a given kind."""

    button: Button
    press: ButtonPress = ButtonPress.SHORT

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
