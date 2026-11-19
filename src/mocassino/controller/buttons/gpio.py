"""The four buttons of the Pimoroni Pirate Audio hat, read via GPIO.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import threading
from functools import partial
from queue import Queue
from typing import Any

from mocassino.controller.events import Button, ButtonEvent, Press

BOUNCE_TIME: float = 0.1
# The pins of the buttons but Y, whose pin depends on the board (see DEFAULT_PIN_BUTTON_Y)
BUTTON_PINS: dict[Button, int] = {Button.A: 5, Button.B: 6, Button.X: 16}
# Boards made before 23 January 2020 have the Y button on pin 20 instead
DEFAULT_PIN_BUTTON_Y: int = 24


class GpioButtonSource:
    """The buttons of the Pirate Audio hat.

    A short press is reported when the button is released before the hold time.
    Otherwise, when the hold time has passed, a long press and a hold press are reported;
    the hold press is then reported again at each repeat time, until the button is released.
    """

    def __init__(
        self,
        long_press_time: float,
        repeat_hold_time: float,
        pin_button_y: int = DEFAULT_PIN_BUTTON_Y,
    ) -> None:
        """Initialize the source.

        :param long_press_time: how long a button must be held for a long press, in seconds
        :param repeat_hold_time: how often the hold press of a held button repeats, in seconds
        :param pin_button_y: the pin of the Y button: 24, or 20 on boards made before 2020
        """
        self._devices: dict[Button, Any] = {}
        self._events: Queue[ButtonEvent] | None = None
        self._long_press_time = long_press_time
        self._pin_button_y = pin_button_y
        self._released: dict[Button, threading.Event] = {}
        self._repeat_hold_time = repeat_hold_time

    def _close_device(self, button: Button) -> None:
        """Release the pin of a button, if it has a device, and stop its repetitions."""
        released = self._released.pop(button, None)
        if released is not None:
            released.set()
        device = self._devices.pop(button, None)
        if device is not None:
            device.close()

    def _on_held(self, events: Queue[ButtonEvent], button: Button) -> None:
        """Report a long press and a hold press, and start repeating the latter."""
        released = self._released[button] = threading.Event()
        events.put(ButtonEvent(button, Press.LONG))
        events.put(ButtonEvent(button, Press.HOLD))
        threading.Thread(
            target=self._repeat,
            args=(events, button, released),
            daemon=True,
            name=f"mocassino-repeat-{button}",
        ).start()

    def _on_released(self, events: Queue[ButtonEvent], button: Button) -> None:
        """Report a short press, unless the button was held: then, stop repeating."""
        released = self._released.pop(button, None)
        if released is None:
            events.put(ButtonEvent(button))
        else:
            released.set()

    def _open_device(self, events: Queue[ButtonEvent], button: Button, pin: int) -> None:
        """Read a button on the given pin, putting its events in the given queue.

        The gpiozero library is imported here, so that it is only needed
        (together with the hardware) when this source is actually used.
        """
        from gpiozero import Button as GpioButton

        device = GpioButton(
            pin,
            pull_up=True,
            bounce_time=BOUNCE_TIME,
            hold_time=self._long_press_time,
        )
        device.when_held = partial(self._on_held, events, button)
        device.when_released = partial(self._on_released, events, button)
        self._devices[button] = device

    def _repeat(
        self,
        events: Queue[ButtonEvent],
        button: Button,
        released: threading.Event,
    ) -> None:
        """Report a hold press at each repeat time, until the button is released."""
        while not released.wait(self._repeat_hold_time):
            events.put(ButtonEvent(button, Press.HOLD))

    def close(self) -> None:
        """Stop producing events, and release the GPIO pins."""
        for released in self._released.values():
            released.set()
        self._released.clear()
        for device in self._devices.values():
            device.close()
        self._devices.clear()
        self._events = None

    @property
    def pins(self) -> dict[Button, int]:
        """The pin of each button."""
        return {**BUTTON_PINS, Button.Y: self._pin_button_y}

    def set_pin_button_y(self, pin: int) -> None:
        """Read the Y button on the given pin from now on.

        If the source has started, the previous pin is released, and the new one is read.

        :param pin: the pin of the Y button: 24, or 20 on boards made before 2020
        """
        if pin == self._pin_button_y:
            return
        self._pin_button_y = pin
        if self._events is not None:
            self._close_device(Button.Y)
            self._open_device(self._events, Button.Y, pin)

    def start(self, events: Queue[ButtonEvent]) -> None:
        """Start putting the events in the given queue."""
        self._events = events
        for button, pin in self.pins.items():
            self._open_device(events, button, pin)
