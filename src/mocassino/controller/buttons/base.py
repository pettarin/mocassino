"""What the service needs from a source of button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from queue import Queue
from typing import Protocol

from mocassino.controller.events import ButtonEvent


class ButtonSource(Protocol):
    """A source of button events."""

    def close(self) -> None:
        """Stop producing events, and release the source."""

    def set_pin_button_y(self, pin: int) -> None:
        """Read the Y button on the given pin, if the source reads the GPIO pins."""

    def start(self, events: Queue[ButtonEvent]) -> None:
        """Start putting the events in the given queue."""
