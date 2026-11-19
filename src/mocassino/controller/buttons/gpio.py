"""The four buttons of the Pimoroni Pirate Audio hat, read via GPIO.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from functools import partial
from queue import Queue
from typing import Any

from mocassino.controller.events import Button, ButtonEvent

BOUNCE_TIME: float = 0.1
# Boards made before 23 January 2020 have the Y button on pin 20 instead of 24
BUTTON_PINS: dict[Button, int] = {Button.A: 5, Button.B: 6, Button.X: 16, Button.Y: 24}


class GpioButtonSource:
    """The buttons of the Pirate Audio hat.

    A long press is reported as soon as the button has been held long enough;
    a short press is reported when the button is released before that.
    """

    def __init__(self, hold_time: float) -> None:
        """Initialize the source.

        :param hold_time: how long a button must be held for a long press, in seconds
        """
        self._devices: list[Any] = []
        self._held: set[Button] = set()
        self._hold_time = hold_time

    def _on_held(self, events: Queue[ButtonEvent], button: Button) -> None:
        """Report a long press."""
        self._held.add(button)
        events.put(ButtonEvent(button, long=True))

    def _on_released(self, events: Queue[ButtonEvent], button: Button) -> None:
        """Report a short press, unless the release ends a long press already reported."""
        if button in self._held:
            self._held.discard(button)
        else:
            events.put(ButtonEvent(button))

    def close(self) -> None:
        """Stop producing events, and release the GPIO pins."""
        for device in self._devices:
            device.close()
        self._devices.clear()

    def start(self, events: Queue[ButtonEvent]) -> None:
        """Start putting the events in the given queue.

        The gpiozero library is imported here, so that it is only needed
        (together with the hardware) when this source is actually used.
        """
        from gpiozero import Button as GpioButton

        for button, pin in BUTTON_PINS.items():
            device = GpioButton(
                pin,
                pull_up=True,
                bounce_time=BOUNCE_TIME,
                hold_time=self._hold_time,
            )
            device.when_held = partial(self._on_held, events, button)
            device.when_released = partial(self._on_released, events, button)
            self._devices.append(device)
