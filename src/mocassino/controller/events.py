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


@dataclass(frozen=True)
class ButtonEvent:
    """A press of a button, either short or long (i.e., the button was held)."""

    button: Button
    long: bool = False
