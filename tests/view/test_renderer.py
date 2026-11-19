"""Tests for the renderer.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest
from PIL import Image, ImageDraw, ImageFont

from mocassino.controller.actions import Action, resolve_button_map
from mocassino.controller.events import Button
from mocassino.model.menu import Menu, MenuCommand, MenuItem
from mocassino.model.moc import MocState, MocStatus
from mocassino.model.settings import Settings
from mocassino.model.state import AppState
from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.icons import ICON_SIZE, draw_icon
from mocassino.view.renderer import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    BAND_WIDTH,
    CONTENT_LEFT,
    CONTENT_RIGHT,
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


def icon(action: Action | None) -> bytes:
    """Return the pixels of the icon of the given action, as drawn next to a button."""
    image = Image.new("RGB", (ICON_SIZE, ICON_SIZE), BACKGROUND_COLOR)
    if action is not None:
        draw_icon(ImageDraw.Draw(image), action, 0, 0, DIM_COLOR)
    return image.tobytes()


def icon_slot(image, button: Button, held: bool) -> bytes:
    """Return the pixels of the place of an icon of the given button.

    The icons of A and X are at the top, those of B and Y at the bottom;
    the icon of the long or hold press is the outer one, that of the short press the inner one.
    """
    left = 2 if button in (Button.A, Button.B) else WIDTH - BAND_WIDTH + 2
    if button in (Button.A, Button.X):
        top = 2 if held else 20
    else:
        top = 222 if held else 204
    return image.crop((left, top, left + ICON_SIZE, top + ICON_SIZE)).tobytes()


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

    def test_button_map_invalid(self):
        with pytest.raises(ValueError, match="is not a valid"):
            Renderer(button_map={"playback": {"A": "rewind"}})

    def test_font_file(self, mocker, tmp_path):
        truetype = mocker.patch(
            "mocassino.view.renderer.ImageFont.truetype",
            return_value=ImageFont.load_default(16),
        )
        path = tmp_path / "font.ttf"
        renderer = Renderer(font_file_path=path)
        renderer.render(AppState())
        assert truetype.call_args_list[0].args == (str(path), 20)

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

    def test_playback_button_icons(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        expected = {
            Button.A: (Action.PLAY_PAUSE, Action.OPEN_MENU),
            Button.B: (Action.NEXT, Action.PREVIOUS),
            Button.X: (Action.VOLUME_UP, Action.SEEK_FORWARD),
            Button.Y: (Action.VOLUME_DOWN, Action.SEEK_BACKWARD),
        }
        for button, (short, held) in expected.items():
            assert icon_slot(image, button, held=False) == icon(short)
            assert icon_slot(image, button, held=True) == icon(held)

    def test_playback_button_icons_are_alone_in_the_bands(self, renderer):
        text = "A very long text that would never fit in the width of the frame"
        status = MocStatus(
            album=text,
            artist=text,
            current_seconds=70,
            file_path="/music/a.flac",
            state=MocState.PLAY,
            title=text,
            total_seconds=205,
        )
        image = renderer.render(AppState(status=status))
        assert not has_content(image, (0, 36, BAND_WIDTH, 204))
        assert not has_content(image, (WIDTH - BAND_WIDTH, 36, WIDTH - 14, 204))
        assert not has_content(image, (WIDTH - 6, 36, WIDTH, 204))
        for left in (0, WIDTH - BAND_WIDTH):
            right = left + BAND_WIDTH
            for top in (0, 18, 36, 202, 220, 238):
                assert not has_content(image, (left, top, right, top + 2))
            assert not has_content(image, (left, 0, left + 2, HEIGHT))
            assert not has_content(image, (right - 2, 0, right, HEIGHT))
        assert not has_content(image, (BAND_WIDTH, 0, CONTENT_LEFT, HEIGHT))
        assert not has_content(image, (CONTENT_RIGHT, 0, WIDTH - BAND_WIDTH, HEIGHT))

    def test_playback_button_icons_follow_the_button_map(self):
        button_map = resolve_button_map(
            {
                "playback": {
                    "A": "next",
                    "A_hold": "seek_forward",
                    "B": "menu_up",
                    "B_hold": None,
                    "X": None,
                    "X_hold": None,
                    "Y_long": "open_menu",
                }
            }
        )
        image = Renderer(button_map=button_map).render(AppState(status=PLAYING))
        expected = {
            Button.A: (Action.NEXT, Action.OPEN_MENU),
            Button.B: (None, None),
            Button.X: (None, None),
            Button.Y: (Action.VOLUME_DOWN, Action.OPEN_MENU),
        }
        for button, (short, held) in expected.items():
            assert icon_slot(image, button, held=False) == icon(short)
            assert icon_slot(image, button, held=True) == icon(held)

    def test_playback_button_icons_not_in_menu_mode(self, renderer):
        state = AppState(menus=[letters_menu(3)])
        without_icons = Renderer(button_map={})
        assert renderer.render(state).tobytes() == without_icons.render(state).tobytes()
        assert renderer.render(AppState()).tobytes() != without_icons.render(AppState()).tobytes()

    def test_playback_button_icons_hidden(self, renderer):
        text = "A very long text that would never fit in the width of the frame"
        status = MocStatus(
            album=text,
            artist=text,
            current_seconds=70,
            file_path="/music/a.flac",
            state=MocState.PLAY,
            title=text,
            total_seconds=205,
        )
        settings = Settings(show_side_icons=False)
        image = renderer.render(AppState(settings=settings, status=status, volume=100))
        defaults = {
            Button.A: (Action.PLAY_PAUSE, Action.OPEN_MENU),
            Button.B: (Action.NEXT, Action.PREVIOUS),
            Button.X: (Action.VOLUME_UP, Action.SEEK_FORWARD),
            Button.Y: (Action.VOLUME_DOWN, Action.SEEK_BACKWARD),
        }
        for button, (short, held) in defaults.items():
            assert icon_slot(image, button, held=False) != icon(short)
            assert icon_slot(image, button, held=True) != icon(held)
        assert not has_content(image, (0, 0, 10, HEIGHT))
        assert not has_content(image, (WIDTH - 10, 0, WIDTH, HEIGHT))
        assert image.getpixel((12, 211)) == ACCENT_COLOR
        assert image.getpixel((WIDTH - 12, 211)) == TRACK_COLOR
        assert has_content(image, (10, 10, 24, 190))
        assert has_content(image, (216, 10, 230, 190))

    def test_playback_button_icons_hidden_with_the_volume_bar(self, renderer):
        settings = Settings(show_side_icons=False)
        quiet = renderer.render(AppState(settings=settings, status=PLAYING, volume=0))
        loud = renderer.render(AppState(settings=settings, status=PLAYING, volume=100))
        assert quiet.tobytes() == loud.tobytes()

    @pytest.mark.parametrize("artist", ["ABBA", "Fabrizio De Andre", "moe.", ""])
    @pytest.mark.parametrize("show_side_icons", [False, True])
    def test_playback_content_is_level_with_the_button_icons(
        self, renderer, show_side_icons, artist
    ):
        settings = Settings(show_side_icons=show_side_icons)
        status = MocStatus(
            album="Album",
            artist=artist,
            current_seconds=70,
            file_path="/music/a.flac",
            state=MocState.PLAY,
            title="Title",
            total_seconds=205,
        )
        image = renderer.render(AppState(settings=settings, status=status))
        left, right = (CONTENT_LEFT, CONTENT_RIGHT) if show_side_icons else (10, WIDTH - 10)
        if artist:
            _, artist_top, _, _ = image.crop((left, 0, right, 22)).getbbox()
            assert artist_top == 2
        else:
            assert not has_content(image, (left, 0, right, 22))
        _, times_top, _, times_bottom = image.crop((left, 218, left + 40, HEIGHT)).getbbox()
        assert times_top + 218 >= 222
        assert times_bottom + 218 == HEIGHT - 2

    @pytest.mark.parametrize(
        ("state", "label"),
        [(MocState.PAUSE, "Paused"), (MocState.PLAY, "Playing"), (MocState.STOP, "Stopped")],
    )
    def test_playback_state_label(self, renderer, state, label):
        status = MocStatus(file_path="/music/a.flac", state=state)
        image = renderer.render(AppState(status=status))
        font, descent = renderer._state_font()
        expected = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_COLOR)
        ImageDraw.Draw(expected).text(
            (WIDTH // 2, HEIGHT - 2 - descent), label, anchor="ms", fill=ACCENT_COLOR, font=font
        )
        box = (80, 218, 160, HEIGHT)
        assert image.crop(box).tobytes() == expected.crop(box).tobytes()
        left, top, right, bottom = expected.getbbox()
        assert abs((left + right) / 2 - WIDTH / 2) <= 1
        assert 222 <= top
        assert bottom <= HEIGHT - 2

    def test_playback_state_label_fits_in_the_height_of_an_icon(self, renderer):
        font, descent = renderer._state_font()
        assert font.size == 17
        boxes = [font.getbbox(label, anchor="ms") for label in ("Paused", "Playing", "Stopped")]
        assert max(box[3] for box in boxes) == descent
        assert descent - min(box[1] for box in boxes) <= ICON_SIZE

    def test_playback_state_label_font_sizes(self, renderer):
        assert renderer._state_font(100)[0].size == 20
        assert renderer._state_font(13)[0].size == 13
        assert renderer._state_font(1)[0].size == 8

    def test_playback_state_labels_share_the_baseline(self, renderer):
        bottoms = {}
        for state in MocState:
            status = MocStatus(file_path="/music/a.flac", state=state)
            image = renderer.render(AppState(status=status))
            bottoms[state] = image.crop((80, 218, 160, HEIGHT)).getbbox()[3] + 218
        assert bottoms[MocState.PLAY] == bottoms[MocState.STOP] == HEIGHT - 2
        assert bottoms[MocState.PAUSE] == HEIGHT - 2 - renderer._state_font()[1]

    def test_playback_has_no_state_icon(self, renderer):
        frames = []
        for state in (MocState.PAUSE, MocState.PLAY):
            status = MocStatus(
                current_seconds=70,
                file_path="/music/a.flac",
                state=state,
                total_seconds=205,
            )
            frames.append(renderer.render(AppState(status=status)))
        paused, playing = frames
        for box in ((0, 0, WIDTH, 218), (0, 218, 80, HEIGHT), (160, 218, WIDTH, HEIGHT)):
            assert paused.crop(box).tobytes() == playing.crop(box).tobytes()
        assert paused.tobytes() != playing.tobytes()

    def test_playback_progress(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        assert image.getpixel((24, 211)) == ACCENT_COLOR
        assert image.getpixel((60, 211)) == ACCENT_COLOR
        assert image.getpixel((200, 211)) == TRACK_COLOR
        assert image.getpixel((215, 211)) == TRACK_COLOR
        assert not has_content(image, (24, 238, 216, HEIGHT))
        assert has_content(image, (24, 222, 70, 238))
        assert has_content(image, (170, 222, 216, 238))

    @pytest.mark.parametrize("show_side_icons", [False, True])
    def test_playback_progress_rows_are_level_with_the_bottom_icons(
        self, renderer, show_side_icons
    ):
        settings = Settings(show_side_icons=show_side_icons)
        image = renderer.render(AppState(settings=settings, status=PLAYING))
        left = CONTENT_LEFT if show_side_icons else 10
        rows = [has_content(image, (left, y, left + 40, y + 1)) for y in range(200, HEIGHT)]
        bar = [y + 200 for y in range(18) if rows[y]]
        assert bar == list(range(208, 216))
        assert bar[0] - 204 == 219 - bar[-1]
        text = [y + 200 for y in range(18, 40) if rows[y]]
        assert 222 <= text[0]
        assert text[-1] == 237

    def test_playback_progress_without_total(self, renderer):
        status = MocStatus(
            current_seconds=70,
            file_path="http://example.com/stream",
            state=MocState.PLAY,
        )
        image = renderer.render(AppState(status=status))
        assert image.getpixel((60, 211)) == TRACK_COLOR
        assert has_content(image, (24, 222, 70, 238))
        assert not has_content(image, (160, 218, 216, HEIGHT))

    def test_playback_stop(self, renderer):
        image = renderer.render(AppState())
        assert has_content(image, (40, 95, 200, 125))
        assert not has_content(image, (CONTENT_LEFT, 130, WIDTH - BAND_WIDTH, 218))
        assert not has_content(image, (CONTENT_LEFT, 218, 80, HEIGHT))
        assert not has_content(image, (160, 218, WIDTH - BAND_WIDTH, HEIGHT))
        assert has_content(image, (80, 218, 160, HEIGHT))

    def test_playback_title_falls_back_to_file_name(self, renderer):
        tagged = MocStatus(file_path="/music/a.flac", state=MocState.PLAY, title="Name")
        untagged = MocStatus(file_path="/music/Name.flac", state=MocState.PLAY)
        box = (CONTENT_LEFT, 24, CONTENT_RIGHT, 150)
        first = renderer.render(AppState(status=tagged)).crop(box)
        second = renderer.render(AppState(status=untagged)).crop(box)
        assert has_content(first, (0, 0, CONTENT_RIGHT - CONTENT_LEFT, 40))
        assert first.tobytes() == second.tobytes()

    def test_playback_track_is_drawn(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        assert has_content(image, (24, 2, 216, 22))
        assert has_content(image, (24, 24, 216, 54))
        assert not has_content(image, (24, 56, 216, 170))
        assert has_content(image, (24, 174, 216, 200))
        assert not has_content(image, (24, 200, 216, 208))

    @pytest.mark.parametrize(
        ("volume", "bottom_color", "top_color"),
        [
            (0, TRACK_COLOR, TRACK_COLOR),
            (50, ACCENT_COLOR, TRACK_COLOR),
            (100, ACCENT_COLOR, ACCENT_COLOR),
        ],
    )
    def test_playback_volume(self, renderer, volume, bottom_color, top_color):
        image = renderer.render(AppState(status=PLAYING, volume=volume))
        assert image.getpixel((229, 199)) == bottom_color
        assert image.getpixel((229, 41)) == top_color

    def test_playback_volume_bar_is_between_the_icons(self, renderer):
        image = renderer.render(AppState(status=PLAYING, volume=50))
        band = image.crop((WIDTH - BAND_WIDTH, 0, WIDTH, HEIGHT))
        bar = [
            (x, y)
            for x in range(BAND_WIDTH)
            for y in range(HEIGHT)
            if band.getpixel((x, y)) in (ACCENT_COLOR, TRACK_COLOR)
        ]
        assert {x for x, _ in bar} == set(range(6, 14))
        assert {y for _, y in bar} == set(range(40, 200))
        assert icon_slot(image, Button.X, held=False) == icon(Action.VOLUME_UP)
        assert icon_slot(image, Button.Y, held=False) == icon(Action.VOLUME_DOWN)

    def test_playback_volume_bar_fills_from_the_bottom(self, renderer):
        image = renderer.render(AppState(status=PLAYING, volume=25))
        column = [image.getpixel((229, y)) for y in range(40, 200)]
        filled = column.count(ACCENT_COLOR)
        assert 38 <= filled <= 42
        assert column == [TRACK_COLOR] * (160 - filled) + [ACCENT_COLOR] * filled

    def test_playback_volume_is_only_on_the_right(self, renderer):
        quiet = renderer.render(AppState(status=PLAYING, volume=0))
        loud = renderer.render(AppState(status=PLAYING, volume=100))
        box = (0, 0, WIDTH - BAND_WIDTH, HEIGHT)
        assert quiet.crop(box).tobytes() == loud.crop(box).tobytes()

    def test_playback_state_does_not_change_the_track_area(self, renderer):
        paused = MocStatus(
            album="Album",
            artist="Artist",
            current_seconds=70,
            file_path="/music/Artist/Album/01.flac",
            state=MocState.PAUSE,
            title="Title",
            total_seconds=205,
        )
        box = (0, 0, WIDTH, 205)
        playing_frame = renderer.render(AppState(status=PLAYING)).crop(box)
        paused_frame = renderer.render(AppState(status=paused)).crop(box)
        assert playing_frame.tobytes() == paused_frame.tobytes()

    def test_playback_title_on_four_lines(self, renderer):
        status = MocStatus(
            album="Album",
            artist="Artist",
            file_path="/music/a.flac",
            state=MocState.PLAY,
            title="One very long title that needs many more than four lines to be shown in full",
        )
        image = renderer.render(AppState(status=status))
        for top in (24, 54, 84, 114):
            assert has_content(image, (CONTENT_LEFT, top + 4, CONTENT_RIGHT, top + 28))
        album = renderer.render(AppState(status=PLAYING)).crop(
            (CONTENT_LEFT, 172, CONTENT_RIGHT, 202)
        )
        assert image.crop((CONTENT_LEFT, 172, CONTENT_RIGHT, 202)).tobytes() == album.tobytes()

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
