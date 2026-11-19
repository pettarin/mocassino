"""The renderer: draws the state of the application into a frame.

The renderer only produces images; showing them is up to a display.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from collections.abc import Mapping
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from mocassino.controller.actions import parse_button_map, resolve_button_map
from mocassino.controller.events import Button, ButtonEvent, Press
from mocassino.model.menu import Menu
from mocassino.model.moc import MocState
from mocassino.model.state import AppState, Mode
from mocassino.view.display.base import HEIGHT, WIDTH
from mocassino.view.icons import ICON_SIZE, draw_icon

type Box = tuple[int, int, int, int]
type Color = tuple[int, int, int]
type Font = ImageFont.FreeTypeFont | ImageFont.ImageFont

ACCENT_COLOR: Color = (255, 176, 0)
BACKGROUND_COLOR: Color = (0, 0, 0)
# In playback mode, a band on each side of the frame is reserved to the icons of the buttons,
# when they are shown: the content is then drawn between CONTENT_LEFT and CONTENT_RIGHT
BAND_WIDTH: int = 20
CONTENT_LEFT: int = BAND_WIDTH + 4
CONTENT_RIGHT: int = WIDTH - BAND_WIDTH - 4
DIM_COLOR: Color = (140, 140, 140)
ELLIPSIS: str = "..."
# The space around the icons of the buttons, and between them
ICON_BORDER: int = 2
MARGIN: int = 10
MENU_ROW_HEIGHT: int = 34
MENU_TITLE_HEIGHT: int = 36
MENU_VISIBLE_ROWS: int = 6
PROGRESS_BAR_HEIGHT: int = 8
SCROLLBAR_WIDTH: int = 4
STATE_LABELS: dict[MocState, str] = {
    MocState.PAUSE: "Paused",
    MocState.PLAY: "Playing",
    MocState.STOP: "Stopped",
}
# The label of the state is written with the largest font size, between these two,
# that makes it as tall as an icon of the buttons at most
STATE_MAX_FONT_SIZE: int = 20
STATE_MIN_FONT_SIZE: int = 8
TEXT_COLOR: Color = (255, 255, 255)
TIMES_FONT_SIZE: int = 20
TRACK_COLOR: Color = (60, 60, 60)
VOLUME_BAR_WIDTH: int = 8


class Renderer:
    """Draws the state of the application into frames of WIDTH x HEIGHT pixels."""

    def __init__(
        self,
        font_file_path: Path | None = None,
        button_map: Mapping[str, Mapping[str, str]] | None = None,
    ) -> None:
        """Initialize the renderer.

        :param font_file_path: the TrueType font; if None, the font built in Pillow
        :param button_map: the button map, in plain form, whose playback actions are shown
                           as icons next to the buttons; if None, the default button map
        :raises OSError: if the font cannot be loaded
        :raises ValueError: if the button map is not valid
        """
        if button_map is None:
            button_map = resolve_button_map({})
        self._button_map = parse_button_map(button_map)
        self._font_file_path = font_file_path
        self._fonts: dict[int, Font] = {}
        self._font(TIMES_FONT_SIZE)

    def _draw_bar(self, draw: ImageDraw.ImageDraw, box: Box, fraction: float) -> None:
        """Draw a horizontal bar, filled from the left for the given fraction."""
        left, top, right, bottom = box
        draw.rectangle(box, fill=TRACK_COLOR)
        filled = round((right - left) * max(0.0, min(1.0, fraction)))
        if filled > 0:
            draw.rectangle((left, top, left + filled, bottom), fill=ACCENT_COLOR)

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
                self._button_map.get((Mode.PLAYBACK, ButtonEvent(button, press))) for press in Press
            ]
            hold, long, short = actions
            held = hold if long is None else long
            if short is not None:
                draw_icon(draw, short, left, inner, DIM_COLOR)
            if held is not None:
                draw_icon(draw, held, left, outer, DIM_COLOR)

    def _draw_menu(self, draw: ImageDraw.ImageDraw, menu: Menu) -> None:
        """Draw a menu: its title, the items around the selected one, and a scrollbar."""
        font = self._font(20)
        draw.rectangle((0, 0, WIDTH - 1, MENU_TITLE_HEIGHT - 1), fill=TRACK_COLOR)
        draw.text(
            (MARGIN, MENU_TITLE_HEIGHT // 2),
            self._fit(menu.title, font, WIDTH - 2 * MARGIN),
            anchor="lm",
            fill=ACCENT_COLOR,
            font=font,
        )
        count = len(menu.items)
        first = min(menu.selected_index - MENU_VISIBLE_ROWS // 2, count - MENU_VISIBLE_ROWS)
        first = max(0, first)
        right = WIDTH - 2 * SCROLLBAR_WIDTH
        for row, item in enumerate(menu.items[first : first + MENU_VISIBLE_ROWS]):
            top = MENU_TITLE_HEIGHT + row * MENU_ROW_HEIGHT
            middle = top + MENU_ROW_HEIGHT // 2
            color = TEXT_COLOR
            if first + row == menu.selected_index:
                draw.rectangle((0, top, right, top + MENU_ROW_HEIGHT - 1), fill=ACCENT_COLOR)
                color = BACKGROUND_COLOR
            elif item.command is None and item.submenu is None:
                color = DIM_COLOR
            label_width = right - 2 * MARGIN
            if item.submenu is not None:
                draw.text((right - MARGIN, middle), ">", anchor="rm", fill=color, font=font)
                label_width -= 2 * MARGIN
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
            draw.rectangle((left, MENU_TITLE_HEIGHT, WIDTH - 1, HEIGHT - 1), fill=TRACK_COLOR)
            draw.rectangle((left, thumb_top, WIDTH - 1, thumb_bottom), fill=DIM_COLOR)

    def _draw_playback(self, draw: ImageDraw.ImageDraw, state: AppState) -> None:
        """Draw the playback: the state, the track, its progress, the volume, and the icons.

        The track takes the top: the artist, the title on up to four lines, and the album.
        At the bottom, the icon of the state followed by the progress bar, with the times.
        The top of the letters of the artist and the bottom of the digits of the times
        leave the same border as the icons of the buttons, so that they are level with them.
        The bottom is level with the two rows of icons of the buttons there:
        the progress bar is centred on the upper row, and the times, with the state
        written between them, take the lower row.
        The icons of the buttons and the volume bar, at the sides, are drawn only if shown.
        """
        status = state.status
        small_font = self._font(TIMES_FONT_SIZE)
        upper_icon_top = HEIGHT - 2 * (ICON_SIZE + ICON_BORDER)
        bar_top = upper_icon_top + (ICON_SIZE - PROGRESS_BAR_HEIGHT) // 2
        left, right = MARGIN, WIDTH - MARGIN
        if state.settings.show_side_icons:
            left, right = CONTENT_LEFT, CONTENT_RIGHT
            self._draw_button_icons(draw)
            self._draw_volume_bar(draw, state.volume)
        width = right - left
        if status.state is MocState.STOP:
            draw.text(
                (WIDTH // 2, 110),
                "Nothing playing",
                anchor="mm",
                fill=DIM_COLOR,
                font=self._font(20),
            )
        else:
            artist_font = self._font(20)
            title_font = self._font(26)
            album_font = self._font(18)
            artist = self._fit(status.artist, artist_font, width)
            draw.text(
                (left, ICON_BORDER - int(artist_font.getbbox(artist)[1])),
                artist,
                fill=DIM_COLOR,
                font=artist_font,
            )
            title = status.title or Path(status.file_path).stem
            for index, line in enumerate(self._wrap(title, title_font, width, 4)):
                draw.text((left, 24 + 30 * index), line, fill=TEXT_COLOR, font=title_font)
            draw.text(
                (left, 174),
                self._fit(status.album, album_font, width),
                fill=DIM_COLOR,
                font=album_font,
            )
            total = status.total_seconds
            self._draw_bar(
                draw,
                (left, bar_top, right - 1, bar_top + PROGRESS_BAR_HEIGHT - 1),
                status.current_seconds / total if total else 0.0,
            )
            draw.text(
                (left, HEIGHT - ICON_BORDER),
                _format_seconds(status.current_seconds),
                anchor="ls",
                fill=TEXT_COLOR,
                font=small_font,
            )
            if total is not None:
                draw.text(
                    (right, HEIGHT - ICON_BORDER),
                    _format_seconds(total),
                    anchor="rs",
                    fill=TEXT_COLOR,
                    font=small_font,
                )
        self._draw_state_label(draw, status.state)

    def _draw_state_label(self, draw: ImageDraw.ImageDraw, state: MocState) -> None:
        """Write the playback state at the bottom of the frame, centred, in the accent colour.

        The three labels share the same baseline, placed so that their letters going
        below it leave the same border as the digits of the times.
        """
        font, descent = self._state_font()
        draw.text(
            (WIDTH // 2, HEIGHT - ICON_BORDER - descent),
            STATE_LABELS[state],
            anchor="ms",
            fill=ACCENT_COLOR,
            font=font,
        )

    def _draw_volume_bar(self, draw: ImageDraw.ImageDraw, volume: int) -> None:
        """Draw the volume as a vertical bar in the band on the right, filled from the bottom.

        The bar is between the icons of X (which by default turns the volume up)
        and those of Y (which by default turns it down).
        """
        reserved = 2 * (ICON_SIZE + ICON_BORDER) + 2 * ICON_BORDER
        top, bottom = reserved, HEIGHT - reserved - 1
        right = WIDTH - (BAND_WIDTH - VOLUME_BAR_WIDTH) // 2 - 1
        left = right - VOLUME_BAR_WIDTH + 1
        draw.rectangle((left, top, right, bottom), fill=TRACK_COLOR)
        filled = round((bottom - top) * max(0.0, min(1.0, volume / 100)))
        if filled > 0:
            draw.rectangle((left, bottom - filled, right, bottom), fill=ACCENT_COLOR)

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
            if self._font_file_path is None:
                self._fonts[size] = ImageFont.load_default(size)
            else:
                self._fonts[size] = ImageFont.truetype(str(self._font_file_path), size)
        return self._fonts[size]

    def _state_font(self, max_height: int = ICON_SIZE) -> tuple[Font, int]:
        """Return the font for the label of the state, and how far it goes below the baseline.

        :param max_height: the height the labels must fit in
        """
        for size in range(STATE_MAX_FONT_SIZE, STATE_MIN_FONT_SIZE - 1, -1):
            font = self._font(size)
            boxes = [font.getbbox(label, anchor="ms") for label in STATE_LABELS.values()]
            ascent = -int(min(box[1] for box in boxes))
            descent = int(max(box[3] for box in boxes))
            if ascent + descent <= max_height:
                break
        return font, descent

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
        """Draw the given state: the current menu, if any, or the playback."""
        image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)
        menu = state.current_menu
        if menu is None:
            self._draw_playback(draw, state)
        else:
            self._draw_menu(draw, menu)
        return image


def _format_seconds(seconds: int) -> str:
    """Format a number of seconds as minutes and seconds (e.g., 70 as 1:10)."""
    return f"{seconds // 60}:{seconds % 60:02d}"
