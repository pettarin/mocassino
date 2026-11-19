"""The LCD of the Pimoroni Pirate Audio hat, driven by an ST7789 controller.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from PIL import Image

from mocassino.view.display.base import HEIGHT, WIDTH

BACKLIGHT_PIN: int = 13
# The frequency of the PWM signal dimming the backlight
BACKLIGHT_PWM_FREQUENCY_HZ: int = 500
CHIP_SELECT: int = 1
DATA_COMMAND_PIN: int = 9
# The commands making the panel stop and resume showing the frame it holds
DISPLAY_OFF_COMMAND: int = 0x28
DISPLAY_ON_COMMAND: int = 0x29
ROTATION: int = 90
SPI_PORT: int = 0
SPI_SPEED_HZ: int = 80_000_000


class St7789Display:
    """The LCD of the Pirate Audio hat."""

    def __init__(self, brightness: float = 1.0) -> None:
        """Initialize the display, and blank the screen.

        The gpiozero and st7789 libraries are imported here, so that they are only needed
        (together with the hardware) when this display is actually used.
        The screen is blanked at once, as after the host boots up the panel
        shows random pixels until the first frame is drawn.
        The st7789 library can only switch the backlight on and off,
        so the backlight is driven here, with a PWM signal dimming it.

        :param brightness: the brightness, between 0.0 and 1.0
        """
        from gpiozero import PWMOutputDevice
        from st7789 import ST7789

        self._brightness = brightness
        self._is_on = True
        self._device = ST7789(
            port=SPI_PORT,
            cs=CHIP_SELECT,
            dc=DATA_COMMAND_PIN,
            backlight=None,
            rotation=ROTATION,
            spi_speed_hz=SPI_SPEED_HZ,
        )
        self._blank()
        self._backlight = PWMOutputDevice(
            BACKLIGHT_PIN,
            frequency=BACKLIGHT_PWM_FREQUENCY_HZ,
            initial_value=brightness,
        )

    def _blank(self) -> None:
        """Show a black frame."""
        self._device.display(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))

    def close(self) -> None:
        """Blank the screen, turn the display off, and release the backlight."""
        self._blank()
        self.turn_off()
        self._backlight.close()

    def set_brightness(self, brightness: float) -> None:
        """Set the brightness of the backlight; while turned off, it applies once on."""
        self._brightness = brightness
        if self._is_on:
            self._backlight.value = brightness

    def show(self, image: Image.Image) -> None:
        """Show the given frame, an RGB image of WIDTH x HEIGHT pixels."""
        self._device.display(image)

    def turn_off(self) -> None:
        """Make the panel stop showing its frame, and turn the backlight off."""
        self._is_on = False
        self._device.command(DISPLAY_OFF_COMMAND)
        self._backlight.value = 0

    def turn_on(self) -> None:
        """Make the panel show its frame again, and turn the backlight on, at its brightness."""
        self._is_on = True
        self._device.command(DISPLAY_ON_COMMAND)
        self._backlight.value = self._brightness
