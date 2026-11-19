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


@pytest.fixture
def display(device_class):
    """A display, with the calls made to the device while initializing it forgotten."""
    display = St7789Display()
    device_class.return_value.reset_mock()
    return display


def assert_black(image):
    """Assert that the image is a black frame."""
    assert image.mode == "RGB"
    assert image.size == (WIDTH, HEIGHT)
    assert image.getextrema() == ((0, 0), (0, 0), (0, 0))


class TestSt7789Display:
    """Tests for the St7789Display class"""

    def test_close(self, device_class, display):
        display.close()
        device = device_class.return_value
        device.display.assert_called_once()
        assert_black(device.display.call_args.args[0])
        device.command.assert_called_once_with(0x28)
        device.set_backlight.assert_called_once_with(0)
        names = [call[0] for call in device.method_calls]
        assert names == ["display", "command", "set_backlight"]

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
        device = device_class.return_value
        device.display.assert_called_once()
        assert_black(device.display.call_args.args[0])
        assert [call[0] for call in device.method_calls] == ["display"]

    def test_show(self, device_class, display):
        image = Image.new("RGB", (WIDTH, HEIGHT))
        display.show(image)
        device_class.return_value.display.assert_called_once_with(image)

    def test_turn_off(self, device_class, display):
        display.turn_off()
        device = device_class.return_value
        device.command.assert_called_once_with(0x28)
        device.set_backlight.assert_called_once_with(0)
        device.display.assert_not_called()

    def test_turn_on(self, device_class, display):
        display.turn_off()
        display.turn_on()
        device = device_class.return_value
        assert [call.args for call in device.command.call_args_list] == [(0x28,), (0x29,)]
        assert [call.args for call in device.set_backlight.call_args_list] == [(0,), (1,)]
        device.display.assert_not_called()
