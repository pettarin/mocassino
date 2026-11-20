"""Tests for the renderer.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest
from PIL import Image, ImageDraw, ImageFont

from mocassino.constants import Action, Button, RightTimerValue
from mocassino.controller.actions import resolve_button_map
from mocassino.model.menu import Menu, MenuCommand, MenuItem
from mocassino.model.moc import MocState, MocStatus
from mocassino.model.settings import Settings
from mocassino.model.state import AppState
from mocassino.view.colors import DEFAULT_COLORS, Colors
from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.icons import ICON_SIZE, draw_icon, draw_state_icon
from mocassino.view.renderer import (
    BAND_WIDTH,
    CONTENT_LEFT,
    CONTENT_RIGHT,
    ELLIPSIS,
    MARGIN,
    MENU_ROW_HEIGHT,
    MENU_TITLE_HEIGHT,
    VOLUME_BAR_TOP,
    Renderer,
    _format_seconds,
)

ACCENT_COLOR = DEFAULT_COLORS.accented
BACKGROUND_COLOR = DEFAULT_COLORS.background
DIM_COLOR = DEFAULT_COLORS.muted
TRACK_COLOR = DEFAULT_COLORS.track

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
        [
            (0, "0:00"),
            (9, "0:09"),
            (70, "1:10"),
            (599, "9:59"),
            (600, "10:00"),
            (3599, "59:59"),
            (3600, "1:00:00"),
            (3725, "1:02:05"),
            (35999, "9:59:59"),
            (36000, "10:00:00"),
            (359999, "99:59:59"),
            (360000, "100:00:00"),
        ],
    )
    def test_format(self, seconds, expected):
        assert _format_seconds(seconds, seconds) == expected

    @pytest.mark.parametrize(
        ("seconds", "length", "expected"),
        [
            (70, 599, "1:10"),
            (70, 600, "01:10"),
            (70, 3599, "01:10"),
            (303, 3725, "0:05:03"),
            (303, 36000, "00:05:03"),
            (3725, 36000, "01:02:05"),
            (0, 359999, "00:00:00"),
        ],
    )
    def test_format_as_the_length(self, seconds, length, expected):
        assert _format_seconds(seconds, length) == expected


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

    @pytest.mark.parametrize(
        ("orientation", "volume_bar"),
        [(90, (139, 229)), (180, (10, 139)), (270, (100, 10))],
    )
    @pytest.mark.parametrize("in_menu", [False, True])
    def test_frame_is_rotated_clockwise(self, renderer, orientation, volume_bar, in_menu):
        menus = [letters_menu(3)] if in_menu else []
        upright = renderer.render(AppState(menus=list(menus), status=PLAYING))
        settings = Settings(display_orientation=orientation)
        rotated = renderer.render(AppState(menus=list(menus), settings=settings, status=PLAYING))
        assert rotated.size == (WIDTH, HEIGHT)
        assert rotated.tobytes() != upright.tobytes()
        assert rotated.rotate(orientation).tobytes() == upright.tobytes()
        if not in_menu:
            # The volume bar, on the right when upright, is where a clockwise turn takes it
            assert upright.getpixel((229, 100)) in (ACCENT_COLOR, TRACK_COLOR)
            assert rotated.getpixel(volume_bar) == upright.getpixel((229, 100))

    def test_frame_is_not_rotated_by_default(self, renderer):
        state = AppState(status=PLAYING)
        assert state.settings.display_orientation == 0
        assert renderer.render(state).getpixel((229, 100)) != BACKGROUND_COLOR

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

    @pytest.mark.parametrize("selected", [False, True])
    def test_menu_checkable_items(self, renderer, selected):
        items = (
            MenuItem(label="Other", command=MenuCommand.BACK),
            MenuItem(label="On", checked=True, command=MenuCommand.TOGGLE_SIDE_ICONS),
            MenuItem(label="Off", checked=False, command=MenuCommand.TOGGLE_SIDE_ICONS),
        )
        frames = {}
        for row in (1, 2):
            menu = Menu(title="Settings", items=items, selected_index=row if selected else 0)
            frames[row] = renderer.render(AppState(menus=[menu]))
        ink, paper = (BACKGROUND_COLOR, ACCENT_COLOR) if selected else ((255, 255, 255), (0, 0, 0))
        left, right = 209, 222
        for row, solid in ((1, True), (2, False)):
            image = frames[row]
            top = row_top(row) + 17 - 7
            for corner in ((left, top), (right, top), (left, top + 13), (right, top + 13)):
                assert image.getpixel(corner) == ink
            assert image.getpixel((left + 1, top + 1)) == ink
            assert image.getpixel((left + 6, top + 6)) == (ink if solid else paper)
            assert image.getpixel((left + 2, top + 2)) == (ink if solid else paper)
            assert image.getpixel((left - 1, top + 6)) == paper
            assert image.getpixel((right + 1, top + 6)) == paper
        plain_row = frames[1].crop((205, row_top(0), 231, row_top(1)))
        assert len(plain_row.getcolors()) == 1

    def test_menu_checkable_item_label_leaves_room_for_the_square(self, renderer):
        label = "A very long label that cannot possibly fit in a row"
        item = MenuItem(label=label, checked=False, command=MenuCommand.TOGGLE_SIDE_ICONS)
        other = MenuItem(label="Other", command=MenuCommand.BACK)
        image = renderer.render(AppState(menus=[Menu(title="Settings", items=(other, item))]))
        assert has_content(image, (10, row_top(1), 190, row_top(2)))
        assert not has_content(image, (199, row_top(1), 209, row_top(2)))

    def test_menu_scrolls_to_the_selected_item(self, renderer):
        image = renderer.render(AppState(menus=[letters_menu(10, selected_index=9)]))
        assert image.getpixel((2, row_top(5) + 2)) == ACCENT_COLOR
        assert image.getpixel((2, row_top(4) + 2)) == BACKGROUND_COLOR
        assert image.getpixel((WIDTH - 2, HEIGHT - 2)) == DIM_COLOR
        assert image.getpixel((WIDTH - 2, MENU_TITLE_HEIGHT + 2)) == TRACK_COLOR

    def test_colors(self, renderer):
        settings = Settings(
            display_colors_accented="red",
            display_colors_background="#00F",
            display_colors_muted="lime",
            display_colors_normal="yellow",
            display_colors_track="Fuchsia",
        )
        colors = Colors(
            accented=(255, 0, 0),
            background=(0, 0, 255),
            muted=(0, 255, 0),
            normal=(255, 255, 0),
            track=(255, 0, 255),
        )
        image = renderer.render(AppState(menus=[letters_menu(10)], settings=settings))
        assert image.getpixel((2, row_top(0) + 2)) == colors.accented
        assert image.getpixel((2, row_top(1) + 2)) == colors.background
        assert image.getpixel((1, 1)) == colors.track
        assert image.getpixel((WIDTH - 2, MENU_TITLE_HEIGHT + 2)) == colors.muted
        assert image.getpixel((WIDTH - 2, HEIGHT - 2)) == colors.track
        assert colors.normal in {color for _, color in image.getcolors(WIDTH * HEIGHT)}

    def test_menu_color_item_has_a_filled_square(self, renderer):
        items = (
            MenuItem(label="Other", command=MenuCommand.BACK),
            MenuItem(label="red [X]", color="red", command=MenuCommand.BACK, value="red"),
            MenuItem(label="#00F", color="#00F"),
        )
        image = renderer.render(AppState(menus=[Menu(title="Colors", items=items)]))
        for row, fill in ((1, (255, 0, 0)), (2, (0, 0, 255))):
            middle = row_top(row) + MENU_ROW_HEIGHT // 2
            assert image.getpixel((215, middle)) == fill
            assert image.getpixel((209, middle)) == (0, 0, 0)
            assert image.getpixel((222, middle)) == (0, 0, 0)

    def test_menu_color_item_label_leaves_room_for_the_square(self, renderer):
        label = "A very long label that cannot possibly fit in a row"
        item = MenuItem(label=label, color="white", command=MenuCommand.BACK, value="white")
        other = MenuItem(label="Other", command=MenuCommand.BACK)
        image = renderer.render(AppState(menus=[Menu(title="Colors", items=(other, item))]))
        assert has_content(image, (10, row_top(1), 190, row_top(2)))
        assert not has_content(image, (199, row_top(1), 208, row_top(2)))

    def test_menu_color_item_selected_shows_the_border(self, renderer):
        item = MenuItem(label="black", color="black", command=MenuCommand.BACK, value="black")
        image = renderer.render(AppState(menus=[Menu(title="Colors", items=(item,))]))
        middle = row_top(0) + MENU_ROW_HEIGHT // 2
        assert image.getpixel((209, middle)) == (0, 0, 0)
        assert image.getpixel((207, middle)) == ACCENT_COLOR

    def test_default_colors(self, renderer):
        image = renderer.render(AppState())
        assert image.getpixel((1, 1)) == DEFAULT_COLORS.background

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
        image = renderer.render(AppState(settings=Settings(show_playlist_bar=False), status=status))
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
                    "B_long": None,
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
        settings = Settings(show_playlist_bar=False, show_side_icons=False, show_volume_bar=False)
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

    def test_playback_volume_bar_hidden(self, renderer):
        settings = Settings(show_volume_bar=False)
        quiet = renderer.render(AppState(settings=settings, status=PLAYING, volume=0))
        loud = renderer.render(AppState(settings=settings, status=PLAYING, volume=100))
        assert quiet.tobytes() == loud.tobytes()
        shown = renderer.render(AppState(status=PLAYING, volume=100))
        assert shown.getpixel((229, 100)) == ACCENT_COLOR
        assert loud.getpixel((229, 100)) == BACKGROUND_COLOR
        band = (WIDTH - BAND_WIDTH, 36, WIDTH, 204)
        assert not has_content(loud, band)
        left = (0, 0, WIDTH - BAND_WIDTH, HEIGHT)
        assert loud.crop(left).tobytes() == shown.crop(left).tobytes()
        for button in (Button.X, Button.Y):
            for held in (False, True):
                assert icon_slot(loud, button, held) == icon_slot(shown, button, held)

    def test_playback_bars_need_the_side_icons(self, renderer):
        text = "A very long text that would never fit in the width of the frame"
        status = MocStatus(
            album=text,
            artist=text,
            current_seconds=205,
            file_path="/music/a.flac",
            state=MocState.PLAY,
            title=text,
            total_seconds=205,
        )
        playlist = ("/music/a.flac",)
        settings = Settings(show_playlist_bar=True, show_side_icons=False, show_volume_bar=True)
        image = renderer.render(
            AppState(playlist=playlist, settings=settings, status=status, volume=100)
        )
        nothing = Settings(show_playlist_bar=False, show_side_icons=False, show_volume_bar=False)
        bare = renderer.render(AppState(playlist=playlist, settings=nothing, status=status))
        assert image.tobytes() == bare.tobytes()
        assert image.getpixel((12, 211)) == ACCENT_COLOR
        assert image.getpixel((WIDTH - 12, 211)) == ACCENT_COLOR
        assert has_content(image, (10, 10, 24, 190))
        assert has_content(image, (CONTENT_RIGHT, 10, WIDTH - 10, 190))
        assert not has_content(image, (0, 0, 10, HEIGHT))
        assert not has_content(image, (WIDTH - 9, 0, WIDTH, HEIGHT))

    def test_playback_progress_bar_hidden(self, renderer):
        settings = Settings(show_progress_bar=False)
        hidden = renderer.render(AppState(settings=settings, status=PLAYING))
        shown = renderer.render(AppState(status=PLAYING))
        assert shown.getpixel((30, 211)) == ACCENT_COLOR
        assert hidden.getpixel((30, 211)) != ACCENT_COLOR
        # the album moves down by 16 pixels, and nothing else changes
        album_shown = shown.crop((CONTENT_LEFT, 180, CONTENT_RIGHT, 206))
        album_hidden = hidden.crop((CONTENT_LEFT, 196, CONTENT_RIGHT, 222))
        assert has_content(album_shown, (0, 0, *album_shown.size))
        assert album_hidden.tobytes() == album_shown.tobytes()
        assert not has_content(hidden, (CONTENT_LEFT, 180, CONTENT_RIGHT, 196))
        above = (0, 0, WIDTH, 180)
        below = (CONTENT_LEFT, 222, CONTENT_RIGHT, HEIGHT)
        sides = [(0, 180, CONTENT_LEFT, HEIGHT), (CONTENT_RIGHT, 180, WIDTH, HEIGHT)]
        for box in (above, below, *sides):
            assert hidden.crop(box).tobytes() == shown.crop(box).tobytes()
        assert has_content(hidden, below)

    @pytest.mark.parametrize(
        ("file_path", "current", "filled"),
        [
            ("/music/1.mp3", 0, 0.25),
            ("/music/2.mp3", 50, 0.5),
            ("/music/4.mp3", 0, 1.0),
            ("/music/other.mp3", 50, 0.0),
        ],
    )
    def test_playback_playlist_bar(self, renderer, file_path, current, filled):
        status = MocStatus(
            current_seconds=current,
            file_path=file_path,
            state=MocState.PLAY,
            title="Title",
            total_seconds=100,
        )
        playlist = ("/music/1.mp3", "/music/2.mp3", "/music/3.mp3", "/music/4.mp3")
        image = renderer.render(AppState(playlist=playlist, status=status))
        top, bottom = VOLUME_BAR_TOP, HEIGHT - VOLUME_BAR_TOP - 1
        boundary = top + round((bottom - top) * filled)
        column = [image.getpixel((10, y)) for y in range(top, bottom + 1)]
        assert set(column) <= {ACCENT_COLOR, TRACK_COLOR}
        if filled > 0:
            assert column[: boundary - top] == [ACCENT_COLOR] * (boundary - top)
        assert column[boundary - top + 1 :] == [TRACK_COLOR] * (bottom - boundary)
        assert image.getpixel((5, 100)) == BACKGROUND_COLOR
        assert image.getpixel((14, 100)) == BACKGROUND_COLOR

    def test_playback_playlist_bar_hidden(self, renderer):
        status = MocStatus(file_path="/music/1.mp3", state=MocState.PLAY, total_seconds=100)
        settings = Settings(show_playlist_bar=False, show_side_icons=False)
        state = AppState(playlist=("/music/1.mp3",), settings=settings, status=status)
        image = renderer.render(state)
        assert not has_content(image, (0, 36, MARGIN, 204))

    @pytest.mark.parametrize("show_playlist_bar", [False, True])
    @pytest.mark.parametrize("show_side_icons", [False, True])
    @pytest.mark.parametrize("show_volume_bar", [False, True])
    def test_playback_bands(self, renderer, show_playlist_bar, show_side_icons, show_volume_bar):
        text = "A very long text that would never fit in the width of the frame"
        status = MocStatus(
            album=text, artist=text, file_path="/music/a.flac", state=MocState.PLAY, title=text
        )
        settings = Settings(
            show_playlist_bar=show_playlist_bar,
            show_side_icons=show_side_icons,
            show_volume_bar=show_volume_bar,
        )
        image = renderer.render(AppState(settings=settings, status=status, volume=50))
        left_band_used = has_content(image, (14, 40, CONTENT_LEFT - 4, 200))
        right_band_used = has_content(image, (CONTENT_RIGHT + 4, 40, WIDTH - BAND_WIDTH + 6, 200))
        assert left_band_used is (not show_side_icons)
        assert right_band_used is (not show_side_icons)
        bar_drawn = image.getpixel((229, 190)) == ACCENT_COLOR
        assert bar_drawn is (show_side_icons and show_volume_bar)
        playlist_bar_drawn = image.getpixel((10, 100)) == TRACK_COLOR
        assert playlist_bar_drawn is (show_side_icons and show_playlist_bar)

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
            _, artist_top, _, artist_bottom = image.crop((left, 0, right, 38)).getbbox()
            assert artist_bottom == 26
            if artist == "ABBA":
                assert artist_top - 2 == 36 - artist_bottom
        else:
            assert not has_content(image, (left, 0, right, 38))
        _, title_top, _, _ = image.crop((left, 38, right, 100)).getbbox()
        assert title_top + 38 == 40
        _, times_top, _, times_bottom = image.crop((left, 218, left + 40, HEIGHT)).getbbox()
        assert times_top + 218 >= 222
        assert times_bottom + 218 == HEIGHT - 2

    @pytest.mark.parametrize("state", list(MocState))
    @pytest.mark.parametrize("show_side_icons", [False, True])
    def test_playback_state_icon(self, renderer, state, show_side_icons):
        settings = Settings(show_side_icons=show_side_icons)
        status = MocStatus(file_path="/music/a.flac", state=state)
        image = renderer.render(AppState(settings=settings, status=status))
        expected = Image.new("RGB", (ICON_SIZE, ICON_SIZE), BACKGROUND_COLOR)
        draw_state_icon(ImageDraw.Draw(expected), state, 0, 0, ACCENT_COLOR)
        left, top = (WIDTH - ICON_SIZE) // 2, HEIGHT - 2 - ICON_SIZE
        box = (left, top, left + ICON_SIZE, top + ICON_SIZE)
        assert image.crop(box).tobytes() == expected.tobytes()
        assert ACCENT_COLOR in {color for _, color in image.crop(box).getcolors()}
        assert not has_content(image, (80, 218, left, HEIGHT))
        assert not has_content(image, (left + ICON_SIZE, 218, 160, HEIGHT))

    @pytest.mark.parametrize(
        ("value", "current", "text"),
        [
            (RightTimerValue.END_TIME, 70, "3:25"),
            (RightTimerValue.REMAINING_TIME, 70, "-2:15"),
            (RightTimerValue.REMAINING_TIME, 205, "-0:00"),
            (RightTimerValue.REMAINING_TIME, 210, "-0:00"),
        ],
    )
    def test_playback_right_timer_value(self, renderer, value, current, text):
        status = MocStatus(
            current_seconds=current,
            file_path="/music/a.flac",
            state=MocState.PLAY,
            total_seconds=205,
        )
        image = renderer.render(AppState(settings=Settings(right_timer_value=value), status=status))
        expected = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_COLOR)
        ImageDraw.Draw(expected).text(
            (CONTENT_RIGHT, HEIGHT - 2),
            text,
            anchor="rs",
            fill=DEFAULT_COLORS.normal,
            font=ImageFont.load_default(20),
        )
        box = (WIDTH // 2 + ICON_SIZE, 218, CONTENT_RIGHT, HEIGHT)
        assert has_content(image, box)
        assert image.crop(box).tobytes() == expected.crop(box).tobytes()

    @pytest.mark.parametrize(
        ("current", "total", "value", "texts"),
        [
            (303, 599, RightTimerValue.END_TIME, ("5:03", "9:59")),
            (303, 754, RightTimerValue.END_TIME, ("05:03", "12:34")),
            (303, 3725, RightTimerValue.END_TIME, ("0:05:03", "1:02:05")),
            (303, 3725, RightTimerValue.REMAINING_TIME, ("0:05:03", "-0:57:02")),
            (45296, 359999, RightTimerValue.END_TIME, ("12:34:56", "99:59:59")),
            (45296, 359999, RightTimerValue.REMAINING_TIME, ("12:34:56", "-87:25:03")),
        ],
    )
    def test_playback_timers_take_the_form_of_the_length(
        self, renderer, current, total, value, texts
    ):
        status = MocStatus(
            current_seconds=current,
            file_path="/music/a.flac",
            state=MocState.PLAY,
            total_seconds=total,
        )
        image = renderer.render(AppState(settings=Settings(right_timer_value=value), status=status))
        expected = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_COLOR)
        font = ImageFont.load_default(20)
        draw = ImageDraw.Draw(expected)
        left_text, right_text = texts
        draw.text(
            (CONTENT_LEFT, HEIGHT - 2),
            left_text,
            anchor="ls",
            fill=DEFAULT_COLORS.normal,
            font=font,
        )
        draw.text(
            (CONTENT_RIGHT, HEIGHT - 2),
            right_text,
            anchor="rs",
            fill=DEFAULT_COLORS.normal,
            font=font,
        )
        icon_left = (WIDTH - ICON_SIZE) // 2
        for box in (
            (CONTENT_LEFT, 218, icon_left, HEIGHT),
            (icon_left + ICON_SIZE, 218, CONTENT_RIGHT, HEIGHT),
        ):
            assert image.crop(box).tobytes() == expected.crop(box).tobytes()

    @pytest.mark.parametrize("value", list(RightTimerValue))
    def test_playback_right_timer_without_total(self, renderer, value):
        status = MocStatus(current_seconds=70, file_path="/music/a.flac", state=MocState.PLAY)
        image = renderer.render(AppState(settings=Settings(right_timer_value=value), status=status))
        assert not has_content(image, (WIDTH // 2 + ICON_SIZE, 218, CONTENT_RIGHT, HEIGHT))

    @pytest.mark.parametrize("state", list(MocState))
    def test_playback_state_icon_hidden_with_the_timers(self, renderer, state):
        settings = Settings(show_progress_bar=False, show_timers=False)
        status = MocStatus(file_path="/music/a.flac", state=state)
        image = renderer.render(AppState(settings=settings, status=status))
        assert not has_content(image, (CONTENT_LEFT, 236, CONTENT_RIGHT, HEIGHT))
        left, top = (WIDTH - ICON_SIZE) // 2, HEIGHT - 2 - ICON_SIZE
        assert not has_content(image, (left, top, left + ICON_SIZE, top + ICON_SIZE))

    @pytest.mark.parametrize("show_side_icons", [False, True])
    def test_playback_timers_hidden(self, renderer, show_side_icons):
        left = CONTENT_LEFT if show_side_icons else 10
        right = CONTENT_RIGHT if show_side_icons else WIDTH - 10
        shown = renderer.render(
            AppState(settings=Settings(show_side_icons=show_side_icons), status=PLAYING)
        )
        settings = Settings(show_side_icons=show_side_icons, show_timers=False)
        hidden = renderer.render(AppState(settings=settings, status=PLAYING))
        # the album and the progress bar move down by one row of icons, into that of the times
        moved = shown.crop((left, 180, right, 216))
        assert has_content(moved, (0, 0, *moved.size))
        assert hidden.crop((left, 198, right, 234)).tobytes() == moved.tobytes()
        assert not has_content(hidden, (left, 180, right, 198))
        assert not has_content(hidden, (left, 234, right, HEIGHT))
        rows = [has_content(hidden, (left, y, left + 40, y + 1)) for y in range(222, HEIGHT)]
        bar = [y + 222 for y, drawn in enumerate(rows) if drawn]
        assert bar == list(range(226, 234))
        assert bar[0] - 222 == 237 - bar[-1]
        # nothing else changes
        above = (0, 0, WIDTH, 180)
        sides = [(0, 180, left, HEIGHT), (right, 180, WIDTH, HEIGHT)]
        for box in (above, *sides):
            assert hidden.crop(box).tobytes() == shown.crop(box).tobytes()

    @pytest.mark.parametrize("album", ["Album", "ABBA GOLD", "moe."])
    def test_playback_timers_and_progress_bar_hidden(self, renderer, album):
        status = MocStatus(album=album, file_path="/music/a.flac", state=MocState.PLAY)
        settings = Settings(show_progress_bar=False, show_timers=False)
        image = renderer.render(AppState(settings=settings, status=status))
        # the album takes the place of the progress bar, moved into the row of the times
        _, _, _, album_bottom = image.crop((CONTENT_LEFT, 186, CONTENT_RIGHT, HEIGHT)).getbbox()
        assert album_bottom + 186 == 234
        assert not has_content(image, (CONTENT_LEFT, 180, CONTENT_RIGHT, 216))

    def test_playback_state_icon_is_level_with_the_bottom_button_icons(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        left = (WIDTH - ICON_SIZE) // 2
        _, top, _, bottom = image.crop((left, 221, left + ICON_SIZE, HEIGHT)).getbbox()
        _, icon_top, _, icon_bottom = image.crop((0, 221, BAND_WIDTH, HEIGHT)).getbbox()
        assert (top, bottom) == (icon_top, icon_bottom)
        assert (top + 221, bottom + 221) == (224, 236)

    def test_playback_state_is_only_shown_by_its_icon(self, renderer):
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
        left = (WIDTH - ICON_SIZE) // 2
        boxes = (
            (0, 0, WIDTH, 222),
            (0, 222, left, HEIGHT),
            (left + ICON_SIZE, 222, WIDTH, HEIGHT),
        )
        for box in boxes:
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
        assert has_content(image, (40, 95, 200, 119))
        assert has_content(image, (40, 121, 200, 145))
        assert not has_content(image, (CONTENT_LEFT, 150, WIDTH - BAND_WIDTH, 218))
        assert not has_content(image, (CONTENT_LEFT, 218, 80, HEIGHT))
        assert not has_content(image, (160, 218, WIDTH - BAND_WIDTH, HEIGHT))
        assert has_content(image, (80, 218, 160, HEIGHT))

    @pytest.mark.parametrize("show_side_icons", [False, True])
    def test_playback_stop_hint_is_centred(self, renderer, show_side_icons):
        settings = Settings(
            show_playlist_bar=show_side_icons,
            show_side_icons=show_side_icons,
            show_volume_bar=show_side_icons,
        )
        image = renderer.render(AppState(settings=settings))
        left, right = (CONTENT_LEFT, CONTENT_RIGHT) if show_side_icons else (10, WIDTH - 10)
        hint_left, hint_top, hint_right, hint_bottom = image.crop((left, 40, right, 200)).getbbox()
        assert abs((left + hint_left) + (left + hint_right) - WIDTH) <= 2
        assert abs((40 + hint_top) + (40 + hint_bottom) - HEIGHT) <= 6
        rows = [has_content(image, (left, y, right, y + 1)) for y in range(40, 200)]
        blocks = sum(1 for index in range(1, len(rows)) if rows[index] and not rows[index - 1])
        assert blocks == 2
        expected = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(expected)
        font = ImageFont.load_default(20)
        draw.text((120, 107), "Press Menu to select", anchor="mm", fill=DIM_COLOR, font=font)
        draw.text((120, 133), "the folder to play", anchor="mm", fill=DIM_COLOR, font=font)
        box = (left, 40, right, 200)
        assert image.crop(box).tobytes() == expected.crop(box).tobytes()

    def test_playback_title_falls_back_to_file_name(self, renderer):
        tagged = MocStatus(file_path="/music/a.flac", state=MocState.PLAY, title="Name")
        untagged = MocStatus(file_path="/music/Name.flac", state=MocState.PLAY)
        box = (CONTENT_LEFT, 38, CONTENT_RIGHT, 165)
        first = renderer.render(AppState(status=tagged)).crop(box)
        second = renderer.render(AppState(status=untagged)).crop(box)
        assert has_content(first, (0, 0, CONTENT_RIGHT - CONTENT_LEFT, 40))
        assert first.tobytes() == second.tobytes()

    def test_playback_track_is_drawn(self, renderer):
        image = renderer.render(AppState(status=PLAYING))
        assert not has_content(image, (24, 0, 216, 10))
        assert has_content(image, (24, 10, 216, 26))
        assert not has_content(image, (24, 26, 216, 40))
        assert has_content(image, (24, 40, 216, 62))
        assert not has_content(image, (24, 62, 216, 184))
        assert has_content(image, (24, 184, 216, 200))
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

    @pytest.mark.parametrize(
        "title", ["Title", "aceno", "blind fold", "Il Vento Caldo Dell'estate"]
    )
    def test_playback_title_starts_at_the_top_of_the_volume_bar(self, renderer, title):
        status = MocStatus(file_path="/music/a.flac", state=MocState.PLAY, title=title)
        image = renderer.render(AppState(status=status))
        _, title_top, _, _ = image.crop((CONTENT_LEFT, 0, CONTENT_RIGHT, 170)).getbbox()
        band = image.crop((WIDTH - BAND_WIDTH + 6, 36, WIDTH - 6, 204))
        _, volume_bar_top, _, _ = band.getbbox()
        assert title_top == volume_bar_top + 36 == 40

    def test_playback_title_empty(self, renderer):
        status = MocStatus(album="Album", artist="Artist", state=MocState.PLAY)
        image = renderer.render(AppState(status=status))
        assert not has_content(image, (CONTENT_LEFT, 38, CONTENT_RIGHT, 170))

    def test_playback_title_on_five_lines(self, renderer):
        status = MocStatus(
            album="Album",
            artist="Artist",
            file_path="/music/a.flac",
            state=MocState.PLAY,
            title="One very long title that needs many more than five lines to be shown, "
            "because it goes on and on and on",
        )
        image = renderer.render(AppState(status=status))
        for top in (38, 68, 98, 128, 158):
            assert has_content(image, (CONTENT_LEFT, top + 4, CONTENT_RIGHT, top + 28))
        album = renderer.render(AppState(status=PLAYING)).crop(
            (CONTENT_LEFT, 185, CONTENT_RIGHT, 206)
        )
        assert image.crop((CONTENT_LEFT, 185, CONTENT_RIGHT, 206)).tobytes() == album.tobytes()
        assert not has_content(image, (CONTENT_LEFT, 184, CONTENT_RIGHT, 185))

    @pytest.mark.parametrize("album", ["Album", "ABBA GOLD", "moe."])
    def test_playback_album_ends_at_the_bottom_of_the_volume_bar(self, renderer, album):
        status = MocStatus(album=album, file_path="/music/a.flac", state=MocState.PLAY)
        image = renderer.render(AppState(status=status))
        _, _, _, album_bottom = image.crop((CONTENT_LEFT, 170, CONTENT_RIGHT, 206)).getbbox()
        band = image.crop((WIDTH - BAND_WIDTH + 6, 36, WIDTH - 6, 204))
        _, _, _, volume_bar_bottom = band.getbbox()
        assert album_bottom + 170 == volume_bar_bottom + 36 == 200

    @pytest.mark.parametrize("album", ["Album", "ABBA GOLD", "moe."])
    def test_playback_album_ends_at_the_bottom_of_the_hidden_progress_bar(self, renderer, album):
        status = MocStatus(album=album, file_path="/music/a.flac", state=MocState.PLAY)
        shown = renderer.render(AppState(status=status))
        settings = Settings(show_progress_bar=False)
        hidden = renderer.render(AppState(settings=settings, status=status))
        _, _, _, album_bottom = hidden.crop((CONTENT_LEFT, 186, CONTENT_RIGHT, 222)).getbbox()
        _, _, _, bar_bottom = shown.crop((CONTENT_LEFT, 204, CONTENT_RIGHT, 220)).getbbox()
        assert album_bottom + 186 == bar_bottom + 204 == 216

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
