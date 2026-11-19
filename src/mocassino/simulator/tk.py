"""A window simulating the Pirate Audio hat: its display and its four buttons.

The window is both a display and a button source.
Tk must run in the main thread, so the application runs in another thread:
the two only exchange frames and button events, through queues.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from functools import partial
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any

from PIL import Image

from mocassino.controller.events import Button, ButtonEvent, Press
from mocassino.view.display.base import HEIGHT, WIDTH

if TYPE_CHECKING:
    import tkinter

# The arrow keys standing for the buttons, by the name Tk gives them
ARROW_KEYS: dict[str, Button] = {
    "Down": Button.Y,
    "Left": Button.A,
    "Right": Button.B,
    "Up": Button.X,
}
# The row and the column of each button in the window, around the display like on the hat
BUTTON_CELLS: dict[Button, tuple[int, int]] = {
    Button.A: (0, 0),
    Button.B: (1, 0),
    Button.X: (0, 2),
    Button.Y: (1, 2),
}
HINT: str = (
    "Click a button, or keep it pressed for a long press, repeated while pressed.\n"
    "Keys: a b x y, or the arrows (left=A, right=B, up=X, down=Y), for a short press;\n"
    "with Shift, for a long press."
)
PADDING: int = 8
POLL_INTERVAL_MS: int = 30
SCALE: int = 2
# The bit of the state of a Tk key event telling that Shift is down
SHIFT_MASK: int = 0x0001
TITLE: str = "mocassino simulator"


class TkSimulator:
    """A window simulating the display and the buttons of the Pirate Audio hat.

    The methods of the display and of the button source can be called from any thread;
    the run method must be called from the main thread.
    """

    def __init__(self, long_press_time: float, repeat_hold_time: float) -> None:
        """Initialize the simulator; the window is created when it is run.

        :param long_press_time: how long a button must be pressed for a long press, in seconds
        :param repeat_hold_time: how often the hold press of a pressed button repeats, in seconds
        """
        self._closed = threading.Event()
        self._events: Queue[ButtonEvent] | None = None
        self._frames: Queue[Image.Image] = Queue()
        self._held: set[Button] = set()
        self._long_press_time = long_press_time
        self._image_tk: Any = None
        self._photo: Any = None
        self._repeat_hold_time = repeat_hold_time
        self._root: Any = None
        self._screen: Any = None
        self._timers: dict[Button, Any] = {}

    def _emit(self, event: ButtonEvent) -> None:
        """Put a button event in the queue, if the source has been started."""
        if self._events is not None:
            self._events.put(event)

    def _on_held(self, button: Button) -> None:
        """Report a long press and a hold press, and start repeating the latter."""
        self._held.add(button)
        self._emit(ButtonEvent(button, Press.LONG))
        self._on_repeat(button)

    def _on_key(self, tk_event: tkinter.Event[tkinter.Misc]) -> None:
        """Report the press of the button named by a key: its letter, or its arrow.

        The arrows are: left for A, right for B, up for X, and down for Y.
        A key alone is a short press; with Shift (i.e., an uppercase letter), it is a button
        held just long enough: a long press and a hold press.
        """
        character = str(tk_event.char)
        if tk_event.keysym in ARROW_KEYS:
            button = ARROW_KEYS[tk_event.keysym]
            held = bool(int(tk_event.state) & SHIFT_MASK)
        elif character and character.upper() in list(Button):
            button = Button(character.upper())
            held = character.isupper()
        else:
            return
        if held:
            self._emit(ButtonEvent(button, Press.LONG))
            self._emit(ButtonEvent(button, Press.HOLD))
        else:
            self._emit(ButtonEvent(button))

    def _on_press(self, button: Button, tk_event: object = None) -> None:
        """Start timing the press of a button of the window."""
        if button not in self._timers:
            delay = int(self._long_press_time * 1000)
            self._timers[button] = self._root.after(delay, partial(self._on_held, button))

    def _on_release(self, button: Button, tk_event: object = None) -> None:
        """Report a short press, unless the button was held: then, stop repeating."""
        timer = self._timers.pop(button, None)
        if timer is not None:
            self._root.after_cancel(timer)
        if button in self._held:
            self._held.discard(button)
        elif timer is not None:
            self._emit(ButtonEvent(button))

    def _on_repeat(self, button: Button) -> None:
        """Report a hold press, and schedule the next one."""
        self._emit(ButtonEvent(button, Press.HOLD))
        delay = int(self._repeat_hold_time * 1000)
        self._timers[button] = self._root.after(delay, partial(self._on_repeat, button))

    def _poll(self) -> None:
        """Show the latest frame received, if any, and close the window when asked to."""
        if self._closed.is_set():
            self._root.quit()
            return
        image = None
        try:
            while True:
                image = self._frames.get_nowait()
        except Empty:
            pass
        if image is not None:
            self._show(image)
        self._root.after(POLL_INTERVAL_MS, self._poll)

    def _show(self, image: Image.Image) -> None:
        """Draw a frame in the window, enlarged."""
        enlarged = image.resize((WIDTH * SCALE, HEIGHT * SCALE), Image.Resampling.NEAREST)
        self._photo = self._image_tk.PhotoImage(enlarged)
        self._screen.configure(image=self._photo)

    def close(self) -> None:
        """Ask the window to close; it can be called more than once."""
        self._closed.set()

    def run(self, on_window_closed: Callable[[], None]) -> None:
        """Create the window and handle it until it is asked to close.

        Closing the window by hand does not close it directly: it calls the given function,
        which is expected to stop the application, which in turn closes its display.

        :param on_window_closed: called when the user closes the window
        """
        tkinter, self._image_tk = _import_tk()
        root = self._root = tkinter.Tk()
        root.title(TITLE)
        root.resizable(False, False)
        self._screen = tkinter.Label(root, borderwidth=0)
        self._screen.grid(row=0, column=1, rowspan=2, padx=PADDING, pady=PADDING)
        self._show(Image.new("RGB", (WIDTH, HEIGHT)))
        for button, (row, column) in BUTTON_CELLS.items():
            widget = tkinter.Button(root, text=button.value, width=3, height=2)
            widget.grid(row=row, column=column, padx=PADDING, pady=PADDING)
            widget.bind("<ButtonPress-1>", partial(self._on_press, button))
            widget.bind("<ButtonRelease-1>", partial(self._on_release, button))
        hint = tkinter.Label(root, text=HINT, justify="left")
        hint.grid(row=2, column=0, columnspan=3, padx=PADDING, pady=(0, PADDING))
        root.bind("<KeyPress>", self._on_key)
        root.protocol("WM_DELETE_WINDOW", on_window_closed)
        root.after(POLL_INTERVAL_MS, self._poll)
        root.mainloop()
        root.destroy()

    def show(self, image: Image.Image) -> None:
        """Show the given frame, an RGB image of WIDTH x HEIGHT pixels."""
        self._frames.put(image)

    def start(self, events: Queue[ButtonEvent]) -> None:
        """Start putting the events in the given queue."""
        self._events = events


def _import_tk() -> tuple[Any, Any]:
    """Import Tk, so that it is only needed when the simulator is actually run."""
    import tkinter

    from PIL import ImageTk

    return tkinter, ImageTk
