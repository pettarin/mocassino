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
# Boards made before 23 January 2020 have the Y button on pin 20 instead of 24
BUTTON_PINS: dict[Button, int] = {Button.A: 5, Button.B: 6, Button.X: 16, Button.Y: 24}


class GpioButtonSource:
    """The buttons of the Pirate Audio hat.

    A short press is reported when the button is released before the hold time.
    Otherwise, when the hold time has passed, a long press and a hold press are reported;
    the hold press is then reported again at each repeat time, until the button is released.
    """

    def __init__(self, long_press_time: float, repeat_hold_time: float) -> None:
        """Initialize the source.

        :param long_press_time: how long a button must be held for a long press, in seconds
        :param repeat_hold_time: how often the hold press of a held button repeats, in seconds
        """
        self._devices: list[Any] = []
        self._long_press_time = long_press_time
        self._released: dict[Button, threading.Event] = {}
        self._repeat_hold_time = repeat_hold_time

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
                hold_time=self._long_press_time,
            )
            device.when_held = partial(self._on_held, events, button)
            device.when_released = partial(self._on_released, events, button)
            self._devices.append(device)
