"""A button source producing no events (e.g., on a PC without the hardware).

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from queue import Queue

from mocassino.controller.events import ButtonEvent


class NullButtonSource:
    """A button source that never produces an event."""

    def close(self) -> None:
        """Release the source; there is nothing to release."""

    def start(self, events: Queue[ButtonEvent]) -> None:
        """Start producing events; none will ever be put in the queue."""
