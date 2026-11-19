"""A display performing no draw action (e.g., on a PC without the hardware).

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from PIL import Image


class NullDisplay:
    """A display that draws nothing; it only remembers the last frame it was given."""

    def __init__(self) -> None:
        """Initialize the display."""
        self.last_image: Image.Image | None = None

    def close(self) -> None:
        """Release the display; there is nothing to release."""

    def show(self, image: Image.Image) -> None:
        """Remember the given frame, without drawing it."""
        self.last_image = image
