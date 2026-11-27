"""The renderer: draws the state of the application into a frame.

The renderer only produces images; showing them is up to a display.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from collections.abc import Mapping
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from mocassino.constants import Button, ButtonPress, Mode, RightTimerValue
from mocassino.controller.actions import parse_button_map, resolve_button_map
from mocassino.controller.events import ButtonEvent
from mocassino.model.colors import parse_color
from mocassino.model.menu import Menu, MenuCommand
from mocassino.model.moc import MocState, MocStatus
from mocassino.model.playlist import playlist_fraction
from mocassino.model.state import AppState
from mocassino.res.font import ROBOTO_REGULAR_FILE_PATH
from mocassino.view.colors import DEFAULT_COLORS, parse_colors
from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.icons import ICON_SIZE, draw_icon, draw_state_icon

type Box = tuple[int, int, int, int]
type Font = ImageFont.FreeTypeFont

# In playback mode, a band on each side of the frame is reserved to the icons of the buttons,
# when they are shown: the content is then drawn between CONTENT_LEFT and CONTENT_RIGHT
BAND_WIDTH: int = 20
CONTENT_LEFT: int = BAND_WIDTH + 4
CONTENT_RIGHT: int = WIDTH - BAND_WIDTH - 4
ELLIPSIS: str = "..."
# The space around the icons of the buttons, and between them
ICON_BORDER: int = 2
MARGIN: int = 10
MENU_CHECK_SIZE: int = 14
MENU_ROW_HEIGHT: int = 34
MENU_TITLE_HEIGHT: int = 36
MENU_VISIBLE_ROWS: int = 6
PROGRESS_BAR_HEIGHT: int = 8
# How a frame is rotated clockwise by each orientation other than 0:
# the names of the transpositions of Pillow count the degrees counter-clockwise
ROTATIONS: dict[int, Image.Transpose] = {
    90: Image.Transpose.ROTATE_270,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_90,
}
SCROLLBAR_WIDTH: int = 4
# The color of the border of the squares showing a color in the menus
SWATCH_BORDER: tuple[int, int, int] = (0, 0, 0)
# What is shown, centred in the frame, when nothing is playing
STOPPED_HINT: tuple[str, ...] = ("Press Menu to select", "the folder to play")
STOPPED_HINT_LINE_HEIGHT: int = 26
TIMES_FONT_SIZE: int = 20
TITLE_MAX_LINES: int = 5
# The first row below the two icons of a button at the top of a band
TOP_ICONS_BOTTOM: int = 2 * (ICON_SIZE + ICON_BORDER)
# The volume bar leaves twice the border between itself and the icons of the buttons
VOLUME_BAR_TOP: int = TOP_ICONS_BOTTOM + 2 * ICON_BORDER
VOLUME_BAR_WIDTH: int = 8


class Renderer:
    """Draws the state of the application into frames of WIDTH x HEIGHT pixels."""

    def __init__(
        self,
        font_file_path: Path | None = None,
        button_map: Mapping[str, Mapping[str, str]] | None = None,
    ) -> None:
        """Initialize the renderer.

        :param font_file_path: the TrueType font; if None, the bundled Roboto Regular
        :param button_map: the button map, in plain form, whose playback actions are shown
                           as icons next to the buttons; if None, the default button map
        :raises OSError: if the font cannot be loaded
        :raises ValueError: if the button map is not valid
        """
        if button_map is None:
            button_map = resolve_button_map({})
        self._button_map = parse_button_map(button_map)
        # The colors to draw with, taken from the settings at each frame
        self._colors = DEFAULT_COLORS
        self._font_file_path = (
            ROBOTO_REGULAR_FILE_PATH if font_file_path is None else font_file_path
        )
        self._fonts: dict[int, Font] = {}
        self._font(TIMES_FONT_SIZE)

    def _draw_bar(self, draw: ImageDraw.ImageDraw, box: Box, fraction: float) -> None:
        """Draw a horizontal bar, filled from the left for the given fraction."""
        left, top, right, bottom = box
        draw.rectangle(box, fill=self._colors.track)
        filled = round((right - left) * max(0.0, min(1.0, fraction)))
        if filled > 0:
            draw.rectangle((left, top, left + filled, bottom), fill=self._colors.accented)

    def _draw_button_icons(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw the icons of the playback actions of the buttons, in the bands at the sides.

        The icons of A and X are at the top of the bands, those of B and Y at the bottom.
        Each button has two icons: at the very top or bottom, that of its long press or,
        if it has none, of its hold press; next to it, towards the middle, that of its
        short press. Actions without an icon leave their place empty.
        """
        step = ICON_SIZE + ICON_BORDER
        for button in Button:
            left = ICON_BORDER
            if button in (Button.X, Button.Y):
                left += WIDTH - BAND_WIDTH
            outer, inner = ICON_BORDER, ICON_BORDER + step
            if button in (Button.B, Button.Y):
                outer, inner = HEIGHT - step, HEIGHT - 2 * step
            actions = [
                self._button_map.get((Mode.PLAYBACK, ButtonEvent(button, press)))
                for press in ButtonPress
            ]
            hold, long, short = actions
            held = hold if long is None else long
            if short is not None:
                draw_icon(draw, short, left, inner, self._colors.muted)
            if held is not None:
                draw_icon(draw, held, left, outer, self._colors.muted)

    def _draw_menu(self, draw: ImageDraw.ImageDraw, menu: Menu) -> None:
        """Draw a menu: its title, the items around the selected one, and a scrollbar.

        On the right of its row, an item with a submenu, or opening the menus to choose
        the music root directory, has an arrow, an item standing for
        a setting that is on or off has a square: solid if on, empty if off,
        and an item standing for a color has a square filled with it.
        """
        font = self._font(20)
        draw.rectangle((0, 0, WIDTH - 1, MENU_TITLE_HEIGHT - 1), fill=self._colors.track)
        draw.text(
            (MARGIN, MENU_TITLE_HEIGHT // 2),
            self._fit(menu.title, font, WIDTH - 2 * MARGIN),
            anchor="lm",
            fill=self._colors.accented,
            font=font,
        )
        count = len(menu.items)
        first = min(menu.selected_index - MENU_VISIBLE_ROWS // 2, count - MENU_VISIBLE_ROWS)
        first = max(0, first)
        right = WIDTH - 2 * SCROLLBAR_WIDTH
        for row, item in enumerate(menu.items[first : first + MENU_VISIBLE_ROWS]):
            top = MENU_TITLE_HEIGHT + row * MENU_ROW_HEIGHT
            middle = top + MENU_ROW_HEIGHT // 2
            color = self._colors.normal
            if first + row == menu.selected_index:
                draw.rectangle(
                    (0, top, right, top + MENU_ROW_HEIGHT - 1),
                    fill=self._colors.accented,
                )
                color = self._colors.background
            elif item.command is None and item.submenu is None:
                color = self._colors.muted
            label_width = right - 2 * MARGIN
            opens_menus = item.command is MenuCommand.CHOOSE_LIBRARY_DIRECTORY
            if item.submenu is not None or opens_menus:
                draw.text((right - MARGIN, middle), ">", anchor="rm", fill=color, font=font)
                label_width -= 2 * MARGIN
            box_top = middle - MENU_CHECK_SIZE // 2
            box = (
                right - MARGIN - MENU_CHECK_SIZE + 1,
                box_top,
                right - MARGIN,
                box_top + MENU_CHECK_SIZE - 1,
            )
            if item.checked is not None:
                draw.rectangle(box, fill=color if item.checked else None, outline=color, width=2)
                label_width -= MENU_CHECK_SIZE + MARGIN
            elif item.color is not None:
                draw.rectangle(box, fill=parse_color(item.color), outline=SWATCH_BORDER, width=2)
                label_width -= MENU_CHECK_SIZE + MARGIN
            draw.text(
                (MARGIN, middle),
                self._fit(item.label, font, label_width),
                anchor="lm",
                fill=color,
                font=font,
            )
        if count > MENU_VISIBLE_ROWS:
            left = WIDTH - SCROLLBAR_WIDTH
            height = HEIGHT - MENU_TITLE_HEIGHT
            thumb_top = MENU_TITLE_HEIGHT + height * first // count
            thumb_bottom = MENU_TITLE_HEIGHT + height * (first + MENU_VISIBLE_ROWS) // count - 1
            draw.rectangle(
                (left, MENU_TITLE_HEIGHT, WIDTH - 1, HEIGHT - 1),
                fill=self._colors.track,
            )
            draw.rectangle((left, thumb_top, WIDTH - 1, thumb_bottom), fill=self._colors.muted)

    def _draw_playback(self, draw: ImageDraw.ImageDraw, state: AppState) -> None:
        """Draw the playback: the state, the track, its progress, the volume, and the icons.

        The track takes the top: the artist, the title on up to five lines, and the album.
        At the bottom, the icon of the state followed by the progress bar, with the times.
        The capital letters of the artist are centred on the icons of the buttons at the top.
        The title starts where the volume bar starts, and the album sits on the line
        where the volume bar ends; without the progress bar, it sits on the line
        where the progress bar would end, leaving no gap above the times.
        The bottom of the digits of the times leaves the same border as the icons.
        The bottom is level with the two rows of icons of the buttons there:
        the progress bar is centred on the upper row, and the times, with the icon
        of the state between them, take the lower row.
        The icons of the buttons, the progress bar, the playlist bar, the volume bar,
        and the times with the icon of the state are drawn only if the settings say so;
        the playlist bar and the volume bar, only if the icons are drawn too.
        The bands on the left and on the right are reserved to the icons and to the bars,
        only when the icons are drawn. Without the times, the progress bar and the album
        move down by one row of icons, into the row the times leave.
        """
        status = state.status
        settings = state.settings
        shift = 0 if settings.show_timers else ICON_SIZE + ICON_BORDER
        upper_icon_top = HEIGHT - 2 * (ICON_SIZE + ICON_BORDER)
        bar_top = upper_icon_top + shift + (ICON_SIZE - PROGRESS_BAR_HEIGHT) // 2
        left, right = MARGIN, WIDTH - MARGIN
        if settings.show_side_icons:
            left, right = CONTENT_LEFT, CONTENT_RIGHT
            self._draw_button_icons(draw)
            if settings.show_playlist_bar:
                self._draw_playlist_bar(draw, playlist_fraction(state.playlist, status))
            if settings.show_volume_bar:
                self._draw_volume_bar(draw, state.volume)
        width = right - left
        if status.state is MocState.STOP:
            for index, line in enumerate(STOPPED_HINT):
                offset = STOPPED_HINT_LINE_HEIGHT * (2 * index + 1 - len(STOPPED_HINT)) // 2
                draw.text(
                    (WIDTH // 2, HEIGHT // 2 + offset),
                    line,
                    anchor="mm",
                    fill=self._colors.muted,
                    font=self._font(20),
                )
        else:
            artist_font = self._font(20)
            title_font = self._font(26)
            album_font = self._font(18)
            capital_height = -int(artist_font.getbbox("A", anchor="ls")[1])
            draw.text(
                (left, (ICON_BORDER + TOP_ICONS_BOTTOM + capital_height) // 2),
                self._fit(status.artist, artist_font, width),
                anchor="ls",
                fill=self._colors.muted,
                font=artist_font,
            )
            title = status.title or Path(status.file_path).stem
            lines = self._wrap(title, title_font, width, TITLE_MAX_LINES)
            title_top = VOLUME_BAR_TOP - int(title_font.getbbox(lines[0])[1]) if lines else 0
            for index, line in enumerate(lines):
                draw.text(
                    (left, title_top + 30 * index),
                    line,
                    fill=self._colors.normal,
                    font=title_font,
                )
            album_bottom = (
                HEIGHT - VOLUME_BAR_TOP + shift
                if settings.show_progress_bar
                else bar_top + PROGRESS_BAR_HEIGHT
            )
            draw.text(
                (left, album_bottom),
                self._fit(status.album, album_font, width),
                anchor="ls",
                fill=self._colors.muted,
                font=album_font,
            )
            total = status.total_seconds
            if settings.show_progress_bar:
                self._draw_bar(
                    draw,
                    (left, bar_top, right - 1, bar_top + PROGRESS_BAR_HEIGHT - 1),
                    status.current_seconds / total if total else 0.0,
                )
        if settings.show_timers:
            self._draw_timers(draw, status, settings.right_timer_value, left, right)

    def _draw_playlist_bar(self, draw: ImageDraw.ImageDraw, fraction: float) -> None:
        """Draw how far the playback has advanced through the playlist, in the band on the left.

        The bar mirrors the volume bar: it is between the icons of A and those of B,
        and it is filled from the top, as the tracks are listed.
        """
        top, bottom = VOLUME_BAR_TOP, HEIGHT - VOLUME_BAR_TOP - 1
        left = (BAND_WIDTH - VOLUME_BAR_WIDTH) // 2
        right = left + VOLUME_BAR_WIDTH - 1
        draw.rectangle((left, top, right, bottom), fill=self._colors.track)
        filled = round((bottom - top) * max(0.0, min(1.0, fraction)))
        if filled > 0:
            draw.rectangle((left, top, right, top + filled), fill=self._colors.accented)

    def _draw_timers(
        self,
        draw: ImageDraw.ImageDraw,
        status: MocStatus,
        right_timer_value: RightTimerValue,
        left: int,
        right: int,
    ) -> None:
        """Draw the times of the track, unless stopped, with the icon of the state between them.

        They take the lower row of the bottom icons: the bottom of the digits of the times
        leaves the same border as the icons. The time on the left is the current one;
        the one on the right, if the length of the track is known, is either its end
        (that length) or the time remaining until then, with a minus sign.
        Both are written in the shortest form fitting the length of the track
        (see _format_seconds).
        """
        if status.state is not MocState.STOP:
            font = self._font(TIMES_FONT_SIZE)
            total = status.total_seconds
            draw.text(
                (left, HEIGHT - ICON_BORDER),
                _format_seconds(status.current_seconds, total or 0),
                anchor="ls",
                fill=self._colors.normal,
                font=font,
            )
            if total is not None:
                if right_timer_value is RightTimerValue.REMAINING_TIME:
                    remaining = max(0, total - status.current_seconds)
                    right_time = f"-{_format_seconds(remaining, total)}"
                else:
                    right_time = _format_seconds(total, total)
                draw.text(
                    (right, HEIGHT - ICON_BORDER),
                    right_time,
                    anchor="rs",
                    fill=self._colors.normal,
                    font=font,
                )
        draw_state_icon(
            draw,
            status.state,
            (WIDTH - ICON_SIZE) // 2,
            HEIGHT - ICON_BORDER - ICON_SIZE,
            self._colors.accented,
        )

    def _draw_volume_bar(self, draw: ImageDraw.ImageDraw, volume: int) -> None:
        """Draw the volume as a vertical bar in the band on the right, filled from the bottom.

        The bar is between the icons of X (which by default turns the volume up)
        and those of Y (which by default turns it down).
        """
        top, bottom = VOLUME_BAR_TOP, HEIGHT - VOLUME_BAR_TOP - 1
        right = WIDTH - (BAND_WIDTH - VOLUME_BAR_WIDTH) // 2 - 1
        left = right - VOLUME_BAR_WIDTH + 1
        draw.rectangle((left, top, right, bottom), fill=self._colors.track)
        filled = round((bottom - top) * max(0.0, min(1.0, volume / 100)))
        if filled > 0:
            draw.rectangle((left, bottom - filled, right, bottom), fill=self._colors.accented)

    def _fit(self, text: str, font: Font, max_width: int) -> str:
        """Return the text, truncated with an ellipsis if wider than the given width."""
        if font.getlength(text) <= max_width:
            return text
        while text and font.getlength(text + ELLIPSIS) > max_width:
            text = text[:-1]
        return text.rstrip() + ELLIPSIS

    def _font(self, size: int) -> Font:
        """Return the font of the given size, loading it the first time."""
        if size not in self._fonts:
            self._fonts[size] = ImageFont.truetype(str(self._font_file_path), size)
        return self._fonts[size]

    def _wrap(self, text: str, font: Font, max_width: int, max_lines: int) -> list[str]:
        """Split the text in at most the given number of lines, breaking it at the spaces.

        What does not fit in the last line is truncated with an ellipsis.
        """
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if current and font.getlength(candidate) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) > max_lines:
            lines = [*lines[: max_lines - 1], " ".join(lines[max_lines - 1 :])]
        return [self._fit(line, font, max_width) for line in lines]

    def render(self, state: AppState) -> Image.Image:
        """Draw the given state: the current menu, if any, or the playback.

        The frame is then rotated clockwise by the orientation of the display in the settings.
        """
        self._colors = parse_colors(state.settings.color_specs())
        image = Image.new("RGB", (WIDTH, HEIGHT), self._colors.background)
        draw = ImageDraw.Draw(image)
        menu = state.current_menu
        if menu is None:
            self._draw_playback(draw, state)
        else:
            self._draw_menu(draw, menu)
        rotation = ROTATIONS.get(state.settings.display_orientation)
        return image if rotation is None else image.transpose(rotation)


def _format_seconds(seconds: int, length: int) -> str:
    """Format a number of seconds as M:SS, MM:SS, H:MM:SS, or HH:MM:SS.

    The form is the shortest one fitting the given length (that of the track),
    so that the times of a track all have the same form: e.g., 303 seconds are 5:03
    in a track of 9:59, 05:03 in one of 12:34, 0:05:03 in one of 1:02:05,
    and 00:05:03 in one of 10:00:00.
    """
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if length < 3600:
        width = 2 if length >= 600 else 1
        return f"{seconds // 60:0{width}d}:{secs:02d}"
    width = 2 if length >= 36000 else 1
    return f"{hours:0{width}d}:{minutes:02d}:{secs:02d}"
