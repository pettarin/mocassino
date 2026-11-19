"""Tests for the button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from mocassino.controller.events import Button, ButtonEvent


class TestButtonEvent:
    """Tests for the ButtonEvent class"""

    def test_short_by_default(self):
        assert ButtonEvent(Button.A) == ButtonEvent(Button.A, long=False)
        assert ButtonEvent(Button.A) != ButtonEvent(Button.A, long=True)

    def test_usable_as_key(self):
        assert {ButtonEvent(Button.X): 1}[ButtonEvent(Button("X"))] == 1
