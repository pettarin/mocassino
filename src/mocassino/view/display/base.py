"""What the service needs from a display.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from typing import Protocol

from PIL import Image

HEIGHT: int = 240
WIDTH: int = 240


class Display(Protocol):
    """A display showing frames of WIDTH x HEIGHT pixels."""

    def close(self) -> None:
        """Release the display; no frame can be shown afterwards."""

    def show(self, image: Image.Image) -> None:
        """Show the given frame, an RGB image of WIDTH x HEIGHT pixels."""
