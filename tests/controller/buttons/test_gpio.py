"""Tests for the buttons of the Pirate Audio hat.

The GPIO pins are simulated by the mock pin factory of gpiozero.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import time
from queue import Empty, Queue

import gpiozero
import pytest
from gpiozero import Device
from gpiozero.pins.mock import MockFactory

from mocassino.constants import Button, ButtonPress
from mocassino.controller.buttons.gpio import (
    BUTTON_PINS,
    BUTTON_Y_PINS,
    ButtonPinError,
    GpioButtonSource,
)
from mocassino.controller.events import ButtonEvent

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


def press(factory, button: Button, duration: float, pin_y: int = 24) -> None:
    """Press a button (its pin is pulled up, so it is driven low) and release it."""
    press_pin(factory, {**BUTTON_PINS, Button.Y: pin_y}[button], duration)


def press_pin(factory, number: int, duration: float) -> None:
    """Drive a pin low, as a pressed button does, and high again."""
    pin = factory.pin(number)
    pin.drive_low()
    time.sleep(duration)
    pin.drive_high()


@pytest.fixture
def failing_pins(mocker):
    """Make the given pins impossible to claim, as the pin library reports it."""
    real = gpiozero.Button
    failing: set[int] = set()

    def button(pin, **kwargs):
        if pin in failing:
            raise RuntimeError("unexpected error")
        return real(pin, **kwargs)

    mocker.patch("gpiozero.Button", side_effect=button)
    return failing


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
        assert events.get(timeout=1) == ButtonEvent(Button.A, ButtonPress.LONG)
        assert events.get(timeout=1) == ButtonEvent(Button.A, ButtonPress.HOLD)
        source.close()
        time.sleep(2 * REPEAT_HOLD_TIME)
        while not events.empty():
            events.get_nowait()
        with pytest.raises(Empty):
            events.get(timeout=3 * REPEAT_HOLD_TIME)

    def test_long_press(self, factory, events, source):
        press(factory, Button.A, LONG_PRESS_TIME + REPEAT_HOLD_TIME / 2)
        assert events.get(timeout=1) == ButtonEvent(Button.A, ButtonPress.LONG)
        assert events.get(timeout=1) == ButtonEvent(Button.A, ButtonPress.HOLD)
        with pytest.raises(Empty):
            events.get(timeout=3 * REPEAT_HOLD_TIME)

    def test_long_press_is_reported_while_held(self, factory, events, source):
        pin = factory.pin(BUTTON_PINS[Button.B])
        pin.drive_low()
        assert events.get(timeout=1) == ButtonEvent(Button.B, ButtonPress.LONG)
        pin.drive_high()

    def test_long_press_repeats_while_held(self, factory, events, source):
        pin = factory.pin(BUTTON_PINS[Button.X])
        pin.drive_low()
        assert events.get(timeout=1) == ButtonEvent(Button.X, ButtonPress.LONG)
        started = time.monotonic()
        for _ in range(4):
            assert events.get(timeout=1) == ButtonEvent(Button.X, ButtonPress.HOLD)
        elapsed = time.monotonic() - started
        assert 2 * REPEAT_HOLD_TIME < elapsed < 6 * REPEAT_HOLD_TIME
        pin.drive_high()
        time.sleep(2 * REPEAT_HOLD_TIME)
        while not events.empty():
            assert events.get_nowait() == ButtonEvent(Button.X, ButtonPress.HOLD)
        with pytest.raises(Empty):
            events.get(timeout=3 * REPEAT_HOLD_TIME)

    def test_pins(self):
        assert BUTTON_PINS == {Button.A: 5, Button.B: 6, Button.X: 16}
        assert BUTTON_Y_PINS == (24, 20)

    @pytest.mark.parametrize("pin", [24, 20])
    def test_button_y_is_read_on_both_pins(self, factory, events, source, pin):
        press(factory, Button.Y, 0.0, pin_y=pin)
        assert events.get(timeout=1) == ButtonEvent(Button.Y)
        with pytest.raises(Empty):
            events.get(timeout=0.2)

    @pytest.mark.parametrize(("failing", "working"), [(20, 24), (24, 20)])
    def test_button_y_pin_that_cannot_be_claimed(
        self, factory, events, failing_pins, caplog, failing, working
    ):
        failing_pins.add(failing)
        source = GpioButtonSource(
            long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME
        )
        with caplog.at_level(logging.DEBUG, logger="mocassino.controller.buttons.gpio"):
            source.start(events)
        assert f"Cannot read the Y button on pin {failing}: unexpected error" in caplog.text
        press(factory, Button.Y, 0.0, pin_y=working)
        assert events.get(timeout=1) == ButtonEvent(Button.Y)
        press(factory, Button.A, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.A)
        source.close()

    def test_button_y_on_no_pin(self, factory, events, failing_pins):
        failing_pins.update(BUTTON_Y_PINS)
        source = GpioButtonSource(
            long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME
        )
        with pytest.raises(
            ButtonPinError,
            match=r"Cannot read the Y button on any pin "
            r"\(pin 24: unexpected error; pin 20: unexpected error\)",
        ):
            source.start(events)
        source.close()
        press(factory, Button.A, 0.0)
        with pytest.raises(Empty):
            events.get(timeout=0.2)

    @pytest.mark.parametrize("button", list(Button))
    def test_short_press(self, factory, events, source, button):
        press(factory, button, 0.0)
        assert events.get(timeout=1) == ButtonEvent(button)
        with pytest.raises(Empty):
            events.get(timeout=0.2)

    def test_short_press_after_long_press(self, factory, events, source):
        press(factory, Button.A, LONG_PRESS_TIME + REPEAT_HOLD_TIME / 2)
        assert events.get(timeout=1) == ButtonEvent(Button.A, ButtonPress.LONG)
        assert events.get(timeout=1) == ButtonEvent(Button.A, ButtonPress.HOLD)
        press(factory, Button.A, 0.0)
        assert events.get(timeout=1) == ButtonEvent(Button.A)
