"""Tests for the display of the Pirate Audio hat.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest
from PIL import Image

from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.display.st7789 import St7789Display


@pytest.fixture
def device_class(mocker):
    """Replace the ST7789 class, so that the hardware is never accessed."""
    return mocker.patch("st7789.ST7789")


class TestSt7789Display:
    """Tests for the St7789Display class"""

    def test_close(self, device_class):
        St7789Display().close()
        device = device_class.return_value
        image = device.display.call_args.args[0]
        assert image.mode == "RGB"
        assert image.size == (WIDTH, HEIGHT)
        assert image.getextrema() == ((0, 0), (0, 0), (0, 0))
        device.set_backlight.assert_called_once_with(0)

    def test_init(self, device_class):
        St7789Display()
        device_class.assert_called_once_with(
            port=0,
            cs=1,
            dc=9,
            backlight=13,
            rotation=90,
            spi_speed_hz=80_000_000,
        )

    def test_show(self, device_class):
        image = Image.new("RGB", (WIDTH, HEIGHT))
        St7789Display().show(image)
        device_class.return_value.display.assert_called_once_with(image)
