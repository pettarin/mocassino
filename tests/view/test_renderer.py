"""Tests for the renderer.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest
from PIL import ImageFont

from mocassino.model.menu import Menu, MenuCommand, MenuItem
from mocassino.model.moc import MocState, MocStatus
from mocassino.model.state import AppState
from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.renderer import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    DIM_COLOR,
    ELLIPSIS,
    MENU_ROW_HEIGHT,
    MENU_TITLE_HEIGHT,
    TRACK_COLOR,
    Renderer,
    _format_seconds,
)

PLAYING = MocStatus(
    album="Album",
    artist="Artist",
    current_seconds=70,
    file_path="/music/Artist/Album/01.flac",
    state=MocState.PLAY,
    title="Title",
    total_seconds=205,
)


def has_content(image, box) -> bool:
    """Tell whether something is drawn inside the given box of the image."""
    return image.crop(box).getbbox() is not None


def letters_menu(count: int, selected_index: int = 0) -> Menu:
    """Build a menu with the given number of items."""
    items = tuple(
        MenuItem(label=f"Item {index}", command=MenuCommand.BACK) for index in range(count)
    )
    return Menu(title="Letters", items=items, selected_index=selected_index)


def row_top(row: int) -> int:
    """Return the vertical position of the given visible row of a menu."""
    return MENU_TITLE_HEIGHT + row * MENU_ROW_HEIGHT


@pytest.fixture
def renderer():
    return Renderer()


class TestFormatSeconds:
    """Tests for the _format_seconds function"""

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [(0, "0:00"), (9, "0:09"), (70, "1:10"), (3725, "62:05")],
    )
    def test_format(self, seconds, expected):
        assert _format_seconds(seconds) == expected


class TestRenderer:
    """Tests for the Renderer class"""

    def test_fit_long_text(self, renderer):
        font = ImageFont.load_default(20)
        text = renderer._fit("A very long label that cannot possibly fit", font, 100)
        assert text.endswith(ELLIPSIS)
        assert text.startswith("A very")
        assert font.getlength(text) <= 100

    def test_fit_short_text(self, renderer):
        assert renderer._fit("Short", ImageFont.load_default(20), 100) == "Short"

    def test_font_file(self, mocker, tmp_path):
        truetype = mocker.patch(
            "mocassino.view.renderer.ImageFont.truetype",
            return_value=ImageFont.load_default(16),
        )
        path = tmp_path / "font.ttf"
        renderer = Renderer(font_file_path=path)
        renderer.render(AppState())
        assert truetype.call_args_list[0].args == (str(path), 16)

    def test_font_file_missing(self, tmp_path):
        with pytest.raises(OSError, match="cannot open resource"):
            Renderer(font_file_path=tmp_path / "missing.ttf")

    def test_frame(self, renderer):
        image = renderer.render(AppState())
        assert image.mode == "RGB"
        assert image.size == (WIDTH, HEIGHT)

    def test_menu_items_are_drawn(self, renderer):
        image = renderer.render(AppState(menus=[letters_menu(3)]))
        assert image.getpixel((1, 1)) == TRACK_COLOR
        assert has_content(image, (10, 4, 200, MENU_TITLE_HEIGHT - 4))
        for row in range(3):
            assert has_content(image, (10, row_top(row) + 4, 200, row_top(row) + 30))
        assert not has_content(image, (0, row_top(3), WIDTH, HEIGHT))

    def test_menu_kinds_of_items(self, renderer):
        items = (
            MenuItem(label="Command", command=MenuCommand.BACK),
            MenuItem(label="Information"),
            MenuItem(label="Submenu", submenu=lambda: letters_menu(1)),
        )
        image = renderer.render(AppState(menus=[Menu(title="Kinds", items=items)]))
        information = image.crop((10, row_top(1), 200, row_top(2)))
        assert DIM_COLOR in {color for _, color in information.getcolors()}
        assert not has_content(image, (205, row_top(1), 231, row_top(2)))
        assert has_content(image, (205, row_top(2), 231, row_top(3)))

    def test_menu_scrolls_to_the_selected_item(self, renderer):
        image = renderer.render(AppState(menus=[letters_menu(10, selected_index=9)]))
        assert image.getpixel((2, row_top(5) + 2)) == ACCENT_COLOR
        assert image.getpixel((2, row_top(4) + 2)) == BACKGROUND_COLOR
        assert image.getpixel((WIDTH - 2, HEIGHT - 2)) == DIM_COLOR
        assert image.getpixel((WIDTH - 2, MENU_TITLE_HEIGHT + 2)) == TRACK_COLOR

    def test_menu_selected_item_is_highlighted(self, renderer):
        menu = letters_menu(3)
        image = renderer.render(AppState(menus=[menu]))
        assert image.getpixel((2, row_top(0) + 2)) == ACCENT_COLOR
        assert image.getpixel((2, row_top(1) + 2)) == BACKGROUND_COLOR
        assert image.getpixel((WIDTH - 2, row_top(1) + 2)) == BACKGROUND_COLOR
        menu.move(1)
        image = renderer.render(AppState(menus=[menu]))
        assert image.getpixel((2, row_top(0) + 2)) == BACKGROUND_COLOR
        assert image.getpixel((2, row_top(1) + 2)) == ACCENT_COLOR

    def test_playback_pause_icon(self, renderer):
        status = MocStatus(file_path="/music/a.flac", state=MocState.PAUSE)
        image = renderer.render(AppState(status=status))
        assert image.getpixel((12, 18)) == ACCENT_COLOR
        assert image.getpixel((18, 18)) == BACKGROUND_COLOR
        assert image.getpixel((24, 18)) == ACCENT_COLOR

    def test_playback_play_icon(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        assert image.getpixel((12, 18)) == ACCENT_COLOR
        assert image.getpixel((24, 11)) == BACKGROUND_COLOR

    def test_playback_progress(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        assert image.getpixel((20, 171)) == ACCENT_COLOR
        assert image.getpixel((200, 171)) == TRACK_COLOR
        assert has_content(image, (10, 180, 60, 200))
        assert has_content(image, (180, 180, 230, 200))

    def test_playback_progress_without_total(self, renderer):
        status = MocStatus(
            current_seconds=70,
            file_path="http://example.com/stream",
            state=MocState.PLAY,
        )
        image = renderer.render(AppState(status=status))
        assert image.getpixel((20, 171)) == TRACK_COLOR
        assert has_content(image, (10, 180, 60, 200))
        assert not has_content(image, (180, 180, 230, 200))

    def test_playback_stop(self, renderer):
        image = renderer.render(AppState())
        assert image.getpixel((24, 11)) == ACCENT_COLOR
        assert has_content(image, (40, 95, 200, 125))
        assert not has_content(image, (0, 130, WIDTH, 205))

    def test_playback_title_falls_back_to_file_name(self, renderer):
        tagged = MocStatus(file_path="/music/a.flac", state=MocState.PLAY, title="Name")
        untagged = MocStatus(file_path="/music/Name.flac", state=MocState.PLAY)
        box = (0, 60, WIDTH, 130)
        first = renderer.render(AppState(status=tagged)).crop(box)
        second = renderer.render(AppState(status=untagged)).crop(box)
        assert has_content(first, (0, 0, WIDTH, 70))
        assert first.tobytes() == second.tobytes()

    def test_playback_track_is_drawn(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        assert has_content(image, (10, 40, 230, 64))
        assert has_content(image, (10, 68, 230, 98))
        assert not has_content(image, (10, 100, 230, 130))
        assert has_content(image, (10, 134, 230, 160))

    @pytest.mark.parametrize(
        ("volume", "left_color", "right_color"),
        [
            (0, TRACK_COLOR, TRACK_COLOR),
            (50, ACCENT_COLOR, TRACK_COLOR),
            (100, ACCENT_COLOR, ACCENT_COLOR),
        ],
    )
    def test_playback_volume(self, renderer, volume, left_color, right_color):
        image = renderer.render(AppState(volume=volume))
        assert image.getpixel((90, 220)) == left_color
        assert image.getpixel((220, 220)) == right_color
        assert has_content(image, (10, 210, 70, 230))

    def test_wrap(self, renderer):
        font = ImageFont.load_default(26)
        assert renderer._wrap("", font, 220, 2) == []
        assert renderer._wrap("Short title", font, 220, 2) == ["Short title"]
        lines = renderer._wrap("Il Vento Caldo Dell'estate", font, 220, 2)
        assert lines == ["Il Vento Caldo", "Dell'estate"]

    def test_wrap_too_many_lines(self, renderer):
        font = ImageFont.load_default(26)
        text = "One very long title that needs many more than two lines to be shown"
        lines = renderer._wrap(text, font, 220, 2)
        assert len(lines) == 2
        assert lines[0] == "One very long title"
        assert lines[1].startswith("that needs")
        assert lines[1].endswith(ELLIPSIS)
        assert all(font.getlength(line) <= 220 for line in lines)
