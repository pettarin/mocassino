"""Tests for the display of the Pirate Audio hat.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest
from PIL import Image

from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.display.st7789 import St7789Display


@pytest.fixture
def backlight_class(mocker):
    """Replace the PWMOutputDevice class, so that the backlight pin is never accessed."""
    return mocker.patch("gpiozero.PWMOutputDevice")


@pytest.fixture
def device_class(mocker):
    """Replace the ST7789 class, so that the hardware is never accessed."""
    return mocker.patch("st7789.ST7789")


@pytest.fixture
def display(backlight_class, device_class):
    """A display, with the calls made to the device while initializing it forgotten."""
    display = St7789Display(brightness=0.4)
    device_class.return_value.reset_mock()
    return display


def assert_black(image):
    """Assert that the image is a black frame."""
    assert image.mode == "RGB"
    assert image.size == (WIDTH, HEIGHT)
    assert image.getextrema() == ((0, 0), (0, 0), (0, 0))


class TestSt7789Display:
    """Tests for the St7789Display class"""

    def test_close(self, backlight_class, device_class, display):
        display.close()
        device = device_class.return_value
        device.display.assert_called_once()
        assert_black(device.display.call_args.args[0])
        device.command.assert_called_once_with(0x28)
        names = [call[0] for call in device.method_calls]
        assert names == ["display", "command"]
        backlight = backlight_class.return_value
        assert backlight.value == 0
        backlight.close.assert_called_once_with()

    def test_init(self, backlight_class, device_class):
        St7789Display()
        device_class.assert_called_once_with(
            port=0,
            cs=1,
            dc=9,
            backlight=None,
            rotation=90,
            spi_speed_hz=80_000_000,
        )
        device = device_class.return_value
        device.display.assert_called_once()
        assert_black(device.display.call_args.args[0])
        assert [call[0] for call in device.method_calls] == ["display"]
        backlight_class.assert_called_once_with(13, frequency=500, initial_value=1.0)

    def test_init_with_brightness(self, backlight_class, device_class):
        St7789Display(brightness=0.25)
        backlight_class.assert_called_once_with(13, frequency=500, initial_value=0.25)

    def test_set_brightness(self, backlight_class, display):
        display.set_brightness(0.75)
        assert backlight_class.return_value.value == 0.75

    def test_set_brightness_while_turned_off(self, backlight_class, display):
        display.turn_off()
        display.set_brightness(0.75)
        backlight = backlight_class.return_value
        assert backlight.value == 0
        display.turn_on()
        assert backlight.value == 0.75

    def test_show(self, device_class, display):
        image = Image.new("RGB", (WIDTH, HEIGHT))
        display.show(image)
        device_class.return_value.display.assert_called_once_with(image)

    def test_turn_off(self, backlight_class, device_class, display):
        display.turn_off()
        device = device_class.return_value
        device.command.assert_called_once_with(0x28)
        device.display.assert_not_called()
        assert backlight_class.return_value.value == 0

    def test_turn_on(self, backlight_class, device_class, display):
        display.turn_off()
        display.turn_on()
        device = device_class.return_value
        assert [call.args for call in device.command.call_args_list] == [(0x28,), (0x29,)]
        device.display.assert_not_called()
        assert backlight_class.return_value.value == 0.4
