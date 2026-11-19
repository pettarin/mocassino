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

from mocassino.controller.buttons.gpio import BUTTON_PINS, GpioButtonSource
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


def press(factory, button: Button, duration: float) -> None:
    """Press a button (its pin is pulled up, so it is driven low) and release it."""
    pin = factory.pin(BUTTON_PINS[button])
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
        assert BUTTON_PINS == {Button.A: 5, Button.B: 6, Button.X: 16, Button.Y: 24}

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
