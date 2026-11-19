"""Tests for the null display.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from PIL import Image

from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.display.null import NullDisplay


class TestNullDisplay:
    """Tests for the NullDisplay class"""

    def test_close(self):
        display = NullDisplay()
        display.close()
        assert display.last_image is None

    def test_show(self):
        image = Image.new("RGB", (WIDTH, HEIGHT))
        display = NullDisplay()
        assert display.last_image is None
        display.show(image)
        assert display.last_image is image

    def test_turn_off_and_on(self):
        display = NullDisplay()
        assert display.is_on is True
        display.turn_off()
        assert display.is_on is False
        display.turn_on()
        assert display.is_on is True
