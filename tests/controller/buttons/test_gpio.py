"""Tests for the buttons of the Pirate Audio hat.

The GPIO pins are simulated by the mock pin factory of gpiozero.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import time
from queue import Empty, Queue

import pytest
from gpiozero import Device
from gpiozero.pins.mock import MockFactory

from mocassino.controller.buttons.gpio import BUTTON_PINS, DEFAULT_PIN_BUTTON_Y, GpioButtonSource
from mocassino.controller.events import Button, ButtonEvent, Press

LONG_PRESS_TIME = 0.05
REPEAT_HOLD_TIME = 0.1


@pytest.fixture
def factory():
    """Replace the GPIO pins with simulated ones."""
    previous = Device.pin_factory
    Device.pin_factory = MockFactory()
    yield Device.pin_factory
    Device.pin_factory.reset()
    Device.pin_factory = previous


@pytest.fixture
def events():
    return Queue()


@pytest.fixture
def source(factory, events):
    source = GpioButtonSource(long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME)
    source.start(events)
    yield source
    source.close()


def press(factory, button: Button, duration: float, pin_button_y: int = 24) -> None:
    """Press a button (its pin is pulled up, so it is driven low) and release it."""
    press_pin(factory, {**BUTTON_PINS, Button.Y: pin_button_y}[button], duration)


def press_pin(factory, number: int, duration: float) -> None:
    """Drive a pin low, as a pressed button does, and high again."""
    pin = factory.pin(number)
    pin.drive_low()
    time.sleep(duration)
    pin.drive_high()


class TestGpioButtonSource:
    """Tests for the GpioButtonSource class"""

    def test_close(self, factory, events):
        source = GpioButtonSource(
            long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME
        )
        source.start(events)
        source.close()
        source.close()
        press(factory, Button.A, 0.0)
        with pytest.raises(Empty):
            events.get(timeout=0.2)

    def test_close_stops_repeating(self, factory, events):
        source = GpioButtonSource(
            long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME
        )
        source.start(events)
        factory.pin(BUTTON_PINS[Button.A]).drive_low()
        assert events.get(timeout=1) == ButtonEvent(Button.A, Press.LONG)
        assert events.get(timeout=1) == ButtonEvent(Button.A, Press.HOLD)
        source.close()
        time.sleep(2 * REPEAT_HOLD_TIME)
        while not events.empty():
            events.get_nowait()
        with pytest.raises(Empty):
            events.get(timeout=3 * REPEAT_HOLD_TIME)

    def test_long_press(self, factory, events, source):
        press(factory, Button.A, LONG_PRESS_TIME + REPEAT_HOLD_TIME / 2)
        assert events.get(timeout=1) == ButtonEvent(Button.A, Press.LONG)
        assert events.get(timeout=1) == ButtonEvent(Button.A, Press.HOLD)
        with pytest.raises(Empty):
            events.get(timeout=3 * REPEAT_HOLD_TIME)

    def test_long_press_is_reported_while_held(self, factory, events, source):
        pin = factory.pin(BUTTON_PINS[Button.B])
        pin.drive_low()
        assert events.get(timeout=1) == ButtonEvent(Button.B, Press.LONG)
        pin.drive_high()

    def test_long_press_repeats_while_held(self, factory, events, source):
        pin = factory.pin(BUTTON_PINS[Button.X])
        pin.drive_low()
        assert events.get(timeout=1) == ButtonEvent(Button.X, Press.LONG)
        started = time.monotonic()
        for _ in range(4):
            assert events.get(timeout=1) == ButtonEvent(Button.X, Press.HOLD)
        elapsed = time.monotonic() - started
        assert 2 * REPEAT_HOLD_TIME < elapsed < 6 * REPEAT_HOLD_TIME
        pin.drive_high()
        time.sleep(2 * REPEAT_HOLD_TIME)
        while not events.empty():
            assert events.get_nowait() == ButtonEvent(Button.X, Press.HOLD)
        with pytest.raises(Empty):
            events.get(timeout=3 * REPEAT_HOLD_TIME)

    def test_pins(self):
        assert BUTTON_PINS == {Button.A: 5, Button.B: 6, Button.X: 16}
        assert DEFAULT_PIN_BUTTON_Y == 24
        source = GpioButtonSource(
            long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME
        )
        assert source.pins == {Button.A: 5, Button.B: 6, Button.X: 16, Button.Y: 24}

    def test_pin_button_y_of_old_boards(self, factory, events):
        source = GpioButtonSource(
            long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME, pin_button_y=20
        )
        assert source.pins[Button.Y] == 20
        source.start(events)
        press_pin(factory, 24, 0.0)
        with pytest.raises(Empty):
            events.get(timeout=0.2)
        press_pin(factory, 20, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.Y)
        source.close()

    def test_set_pin_button_y_before_start(self, factory, events):
        source = GpioButtonSource(
            long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME
        )
        source.set_pin_button_y(20)
        source.start(events)
        press_pin(factory, 20, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.Y)
        source.close()

    def test_set_pin_button_y_while_running(self, factory, events, source):
        press_pin(factory, 24, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.Y)
        source.set_pin_button_y(20)
        assert source.pins[Button.Y] == 20
        press_pin(factory, 24, 0.0)
        with pytest.raises(Empty):
            events.get(timeout=0.2)
        press_pin(factory, 20, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.Y)
        press(factory, Button.A, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.A)
        source.set_pin_button_y(24)
        press_pin(factory, 24, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.Y)

    def test_set_pin_button_y_stops_repeating(self, factory, events, source):
        factory.pin(24).drive_low()
        assert events.get(timeout=1) == ButtonEvent(Button.Y, Press.LONG)
        assert events.get(timeout=1) == ButtonEvent(Button.Y, Press.HOLD)
        source.set_pin_button_y(20)
        time.sleep(2 * REPEAT_HOLD_TIME)
        while not events.empty():
            events.get_nowait()
        with pytest.raises(Empty):
            events.get(timeout=3 * REPEAT_HOLD_TIME)
        factory.pin(24).drive_high()

    def test_set_pin_button_y_to_the_same_pin(self, factory, events, source):
        device = source._devices[Button.Y]
        source.set_pin_button_y(24)
        assert source._devices[Button.Y] is device

    @pytest.mark.parametrize("button", list(Button))
    def test_short_press(self, factory, events, source, button):
        press(factory, button, 0.0)
        assert events.get(timeout=1) == ButtonEvent(button)
        with pytest.raises(Empty):
            events.get(timeout=0.2)

    def test_short_press_after_long_press(self, factory, events, source):
        press(factory, Button.A, LONG_PRESS_TIME + REPEAT_HOLD_TIME / 2)
        assert events.get(timeout=1) == ButtonEvent(Button.A, Press.LONG)
        assert events.get(timeout=1) == ButtonEvent(Button.A, Press.HOLD)
        press(factory, Button.A, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.A)
