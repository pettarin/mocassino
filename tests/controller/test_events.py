"""Tests for the button events.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from mocassino.controller.events import Button, ButtonEvent, Press


class TestButtonEvent:
    """Tests for the ButtonEvent class"""

    def test_short_by_default(self):
        assert ButtonEvent(Button.A) == ButtonEvent(Button.A, Press.SHORT)
        assert ButtonEvent(Button.A) != ButtonEvent(Button.A, Press.LONG)

    def test_three_kinds_of_press(self):
        events = {ButtonEvent(Button.A, press) for press in Press}
        assert len(events) == 3
        assert [press.value for press in Press] == ["hold", "long", "short"]

    def test_usable_as_key(self):
        assert {ButtonEvent(Button.X): 1}[ButtonEvent(Button("X"))] == 1
