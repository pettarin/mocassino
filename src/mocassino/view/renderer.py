"""The renderer: draws the state of the application into a frame.

The renderer only produces images; showing them is up to a display.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from mocassino.model.menu import Menu
from mocassino.model.moc import MocState
from mocassino.model.state import AppState
from mocassino.view.display.base import HEIGHT, WIDTH

type Box = tuple[int, int, int, int]
type Color = tuple[int, int, int]
type Font = ImageFont.FreeTypeFont | ImageFont.ImageFont

ACCENT_COLOR: Color = (255, 176, 0)
BACKGROUND_COLOR: Color = (0, 0, 0)
DIM_COLOR: Color = (140, 140, 140)
ELLIPSIS: str = "..."
MARGIN: int = 10
MENU_ROW_HEIGHT: int = 34
MENU_TITLE_HEIGHT: int = 36
MENU_VISIBLE_ROWS: int = 6
PROGRESS_BAR_BOX: Box = (MARGIN, 168, WIDTH - MARGIN - 1, 175)
SCROLLBAR_WIDTH: int = 4
STATE_ICON_BOX: Box = (10, 10, 26, 26)
STATE_LABELS: dict[MocState, str] = {
    MocState.PAUSE: "Paused",
    MocState.PLAY: "Playing",
    MocState.STOP: "Stopped",
}
TEXT_COLOR: Color = (255, 255, 255)
TRACK_COLOR: Color = (60, 60, 60)
VOLUME_BAR_BOX: Box = (80, 216, WIDTH - MARGIN - 1, 223)


class Renderer:
    """Draws the state of the application into frames of WIDTH x HEIGHT pixels."""

    def __init__(self, font_file_path: Path | None = None) -> None:
        """Initialize the renderer.

        :param font_file_path: the TrueType font; if None, the font built in Pillow
        :raises OSError: if the font cannot be loaded
        """
        self._font_file_path = font_file_path
        self._fonts: dict[int, Font] = {}
        self._font(16)

    def _draw_bar(self, draw: ImageDraw.ImageDraw, box: Box, fraction: float) -> None:
        """Draw a horizontal bar, filled from the left for the given fraction."""
        left, top, right, bottom = box
        draw.rectangle(box, fill=TRACK_COLOR)
        filled = round((right - left) * max(0.0, min(1.0, fraction)))
        if filled > 0:
            draw.rectangle((left, top, left + filled, bottom), fill=ACCENT_COLOR)

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
        """Draw the playback: the state, the track, its progress, and the volume."""
        status = state.status
        small_font = self._font(16)
        width = WIDTH - 2 * MARGIN
        self._draw_state_icon(draw, status.state)
        draw.text(
            (36, 18),
            STATE_LABELS[status.state],
            anchor="lm",
            fill=DIM_COLOR,
            font=small_font,
        )
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
            draw.text(
                (MARGIN, 40),
                self._fit(status.artist, artist_font, width),
                fill=DIM_COLOR,
                font=artist_font,
            )
            title = status.title or Path(status.file_path).stem
            for index, line in enumerate(self._wrap(title, title_font, width, 2)):
                draw.text((MARGIN, 68 + 30 * index), line, fill=TEXT_COLOR, font=title_font)
            draw.text(
                (MARGIN, 134),
                self._fit(status.album, album_font, width),
                fill=DIM_COLOR,
                font=album_font,
            )
            total = status.total_seconds
            self._draw_bar(
                draw,
                PROGRESS_BAR_BOX,
                status.current_seconds / total if total else 0.0,
            )
            draw.text(
                (MARGIN, 180),
                _format_seconds(status.current_seconds),
                fill=TEXT_COLOR,
                font=small_font,
            )
            if total is not None:
                draw.text(
                    (WIDTH - MARGIN, 180),
                    _format_seconds(total),
                    anchor="ra",
                    fill=TEXT_COLOR,
                    font=small_font,
                )
        draw.text(
            (MARGIN, 220),
            f"Vol {state.volume}",
            anchor="lm",
            fill=DIM_COLOR,
            font=small_font,
        )
        self._draw_bar(draw, VOLUME_BAR_BOX, state.volume / 100)

    def _draw_state_icon(self, draw: ImageDraw.ImageDraw, state: MocState) -> None:
        """Draw the icon of the playback state: a triangle, two bars, or a square."""
        left, top, right, bottom = STATE_ICON_BOX
        if state is MocState.PLAY:
            draw.polygon(
                [(left, top), (right, (top + bottom) // 2), (left, bottom)],
                fill=ACCENT_COLOR,
            )
        elif state is MocState.PAUSE:
            draw.rectangle((left, top, left + 5, bottom), fill=ACCENT_COLOR)
            draw.rectangle((right - 5, top, right, bottom), fill=ACCENT_COLOR)
        else:
            draw.rectangle(STATE_ICON_BOX, fill=ACCENT_COLOR)

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
