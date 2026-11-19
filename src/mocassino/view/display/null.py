"""A display performing no draw action (e.g., on a PC without the hardware).

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from PIL import Image


class NullDisplay:
    """A display that draws nothing.

    It only remembers the last frame it was given, its brightness, and whether it is turned on.
    """

    def __init__(self) -> None:
        """Initialize the display."""
        self.brightness: float = 1.0
        self.is_on: bool = True
        self.last_image: Image.Image | None = None

    def close(self) -> None:
        """Release the display; there is nothing to release."""

    def set_brightness(self, brightness: float) -> None:
        """Remember the given brightness."""
        self.brightness = brightness

    def show(self, image: Image.Image) -> None:
        """Remember the given frame, without drawing it."""
        self.last_image = image

    def turn_off(self) -> None:
        """Remember that the display is turned off."""
        self.is_on = False

    def turn_on(self) -> None:
        """Remember that the display is turned on."""
        self.is_on = True
