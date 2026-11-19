"""Tests for the state of the application.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from mocassino.model.menu import Menu, MenuItem
from mocassino.model.moc import MocStatus
from mocassino.model.settings import Settings
from mocassino.model.state import AppState, Mode


class TestAppState:
    """Tests for the AppState class"""

    def test_change_volume(self):
        state = AppState(volume=50)
        assert state.change_volume(5) == 55
        assert state.change_volume(-15) == 40
        assert state.volume == 40

    def test_change_volume_is_clamped(self):
        state = AppState(volume=98)
        assert state.change_volume(5) == 100
        state.volume = 3
        assert state.change_volume(-5) == 0

    def test_defaults(self):
        state = AppState()
        assert state.current_menu is None
        assert state.menus == []
        assert state.mode == Mode.PLAYBACK
        assert state.settings == Settings(show_side_icons=True)
        assert state.status == MocStatus()
        assert state.volume == 50

    def test_menus(self):
        first = Menu(title="First", items=())
        second = Menu(title="Second", items=())
        state = AppState()
        state.open_menu(first)
        assert state.mode == Mode.MENU
        assert state.current_menu is first
        state.open_menu(second)
        assert state.current_menu is second
        state.pop_menu()
        assert state.current_menu is first
        state.pop_menu()
        assert state.mode == Mode.PLAYBACK
        state.pop_menu()
        assert state.mode == Mode.PLAYBACK

    def test_defaults_are_not_shared(self):
        first, second = AppState(), AppState()
        first.settings.show_side_icons = False
        assert second.settings == Settings(show_side_icons=True)

    def test_menu_replaced(self):
        items = (MenuItem(label="a"), MenuItem(label="b"), MenuItem(label="c"))
        state = AppState()
        state.open_menu(Menu(title="Below", items=()))
        state.open_menu(Menu(title="Old", items=items, selected_index=2))
        state.replace_menu(Menu(title="New", items=items))
        assert [menu.title for menu in state.menus] == ["Below", "New"]
        assert state.current_menu.selected_index == 2
        state.replace_menu(Menu(title="Shorter", items=items[:2]))
        assert state.current_menu.selected_index == 1
        state.replace_menu(Menu(title="Empty", items=()))
        assert state.current_menu.selected_index == 0

    def test_menu_replaced_without_menus(self):
        state = AppState()
        state.replace_menu(Menu(title="New", items=()))
        assert [menu.title for menu in state.menus] == ["New"]

    def test_menus_closed_at_once(self):
        state = AppState()
        state.open_menu(Menu(title="First", items=()))
        state.open_menu(Menu(title="Second", items=()))
        state.close_menus()
        assert state.current_menu is None
        assert state.mode == Mode.PLAYBACK
