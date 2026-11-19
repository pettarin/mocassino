"""The LCD of the Pimoroni Pirate Audio hat, driven by an ST7789 controller.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from PIL import Image

from mocassino.view.display.base import HEIGHT, WIDTH

BACKLIGHT_PIN: int = 13
CHIP_SELECT: int = 1
DATA_COMMAND_PIN: int = 9
ROTATION: int = 90
SPI_PORT: int = 0
SPI_SPEED_HZ: int = 80_000_000


class St7789Display:
    """The LCD of the Pirate Audio hat."""

    def __init__(self) -> None:
        """Initialize the display.

        The st7789 library is imported here, so that it is only needed
        (together with the hardware) when this display is actually used.
        """
        from st7789 import ST7789

        self._device = ST7789(
            port=SPI_PORT,
            cs=CHIP_SELECT,
            dc=DATA_COMMAND_PIN,
            backlight=BACKLIGHT_PIN,
            rotation=ROTATION,
            spi_speed_hz=SPI_SPEED_HZ,
        )

    def close(self) -> None:
        """Blank the screen and turn the backlight off."""
        self._device.display(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))
        self._device.set_backlight(0)

    def show(self, image: Image.Image) -> None:
        """Show the given frame, an RGB image of WIDTH x HEIGHT pixels."""
        self._device.display(image)
