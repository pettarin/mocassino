"""Tests for the null button source.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from queue import Queue

from mocassino.controller.buttons.null import NullButtonSource


class TestNullButtonSource:
    """Tests for the NullButtonSource class"""

    def test_no_events(self):
        events = Queue()
        source = NullButtonSource()
        source.start(events)
        source.close()
        assert events.empty()
