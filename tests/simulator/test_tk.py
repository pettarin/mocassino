"""Tests for the simulator.

Tk is replaced by mocks, so that the tests need no screen and open no window.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from queue import Queue
from types import SimpleNamespace

import pytest
from PIL import Image

from mocassino.controller.events import Button, ButtonEvent, Press
from mocassino.simulator.tk import (
    BUTTON_CELLS,
    HINT,
    POLL_INTERVAL_MS,
    SCALE,
    TITLE,
    TkSimulator,
    _import_tk,
)
from mocassino.view.display.base import HEIGHT, WIDTH

LONG_PRESS_TIME = 0.5
REPEAT_HOLD_TIME = 0.2


def arrow(name: str, shift: bool = False) -> SimpleNamespace:
    """Build the Tk event of an arrow key, possibly with Shift and other modifiers down."""
    return SimpleNamespace(char="", keysym=name, state=0x0011 if shift else 0x0010)


def key(character: str) -> SimpleNamespace:
    """Build the Tk event of a key producing a character."""
    return SimpleNamespace(char=character, keysym=character or "Shift_L", state=0)


@pytest.fixture
def tk(mocker):
    """Replace Tk; the mock has the tkinter module, the root window, and the widgets."""
    tk = mocker.Mock()
    tk.buttons = []

    def new_button(*args, **kwargs):
        tk.buttons.append(mocker.Mock(arguments=kwargs))
        return tk.buttons[-1]

    tk.tkinter.Button.side_effect = new_button
    tk.tkinter.Label.side_effect = lambda *args, **kwargs: mocker.Mock(arguments=kwargs)
    tk.root = tk.tkinter.Tk.return_value
    tk.root.after.side_effect = lambda delay, function: (delay, function)
    mocker.patch("mocassino.simulator.tk._import_tk", return_value=(tk.tkinter, tk.image_tk))
    return tk


@pytest.fixture
def events():
    return Queue()


@pytest.fixture
def on_window_closed(mocker):
    return mocker.Mock()


@pytest.fixture
def simulator(tk, events, on_window_closed):
    """A simulator whose window has been created, and whose source has been started."""
    simulator = TkSimulator(long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME)
    simulator.start(events)
    simulator.run(on_window_closed)
    return simulator


class TestImportTk:
    """Tests for the _import_tk function"""

    def test_modules(self):
        tkinter, image_tk = _import_tk()
        assert tkinter.__name__ == "tkinter"
        assert image_tk.__name__ == "PIL.ImageTk"


class TestTkSimulator:
    """Tests for the TkSimulator class"""

    @pytest.mark.parametrize(
        ("name", "button"),
        [("Down", Button.Y), ("Left", Button.A), ("Right", Button.B), ("Up", Button.X)],
    )
    def test_arrow_key(self, simulator, events, name, button):
        simulator._on_key(arrow(name))
        assert events.get_nowait() == ButtonEvent(button)
        assert events.empty()

    @pytest.mark.parametrize(
        ("name", "button"),
        [("Down", Button.Y), ("Left", Button.A), ("Right", Button.B), ("Up", Button.X)],
    )
    def test_arrow_key_with_shift(self, simulator, events, name, button):
        simulator._on_key(arrow(name, shift=True))
        assert events.get_nowait() == ButtonEvent(button, Press.LONG)
        assert events.get_nowait() == ButtonEvent(button, Press.HOLD)
        assert events.empty()

    def test_click(self, simulator, tk, events):
        simulator._on_press(Button.A)
        delay, _ = tk.root.after.call_args.args
        assert delay == 500
        assert events.empty()
        simulator._on_release(Button.A)
        tk.root.after_cancel.assert_called_once()
        assert events.get_nowait() == ButtonEvent(Button.A)
        assert events.empty()

    def test_click_is_timed_once(self, simulator, tk):
        calls = tk.root.after.call_count
        simulator._on_press(Button.A)
        simulator._on_press(Button.A)
        assert tk.root.after.call_count == calls + 1

    def test_close_ends_the_window(self, simulator, tk):
        simulator.close()
        simulator.close()
        calls = tk.root.after.call_count
        simulator._poll()
        tk.root.quit.assert_called_once_with()
        assert tk.root.after.call_count == calls

    def test_events_before_start_are_dropped(self, tk, on_window_closed):
        simulator = TkSimulator(long_press_time=LONG_PRESS_TIME, repeat_hold_time=REPEAT_HOLD_TIME)
        simulator.run(on_window_closed)
        simulator._on_key(key("a"))

    @pytest.mark.parametrize(
        ("character", "event"),
        [
            ("a", ButtonEvent(Button.A)),
            ("b", ButtonEvent(Button.B)),
            ("x", ButtonEvent(Button.X)),
            ("y", ButtonEvent(Button.Y)),
        ],
    )
    def test_key(self, simulator, events, character, event):
        simulator._on_key(key(character))
        assert events.get_nowait() == event
        assert events.empty()

    @pytest.mark.parametrize(("character", "button"), [("A", Button.A), ("Y", Button.Y)])
    def test_key_uppercase(self, simulator, tk, events, character, button):
        calls = tk.root.after.call_count
        simulator._on_key(key(character))
        assert events.get_nowait() == ButtonEvent(button, Press.LONG)
        assert events.get_nowait() == ButtonEvent(button, Press.HOLD)
        assert events.empty()
        assert tk.root.after.call_count == calls

    @pytest.mark.parametrize("character", ["", "q", "1", " "])
    def test_key_of_no_button(self, simulator, events, character):
        simulator._on_key(key(character))
        assert events.empty()

    @pytest.mark.parametrize("name", ["Home", "Next", "Return", "KP_Up"])
    def test_key_of_no_button_without_character(self, simulator, events, name):
        simulator._on_key(arrow(name))
        assert events.empty()

    def test_long_click(self, simulator, tk, events):
        simulator._on_press(Button.B)
        _, on_held = tk.root.after.call_args.args
        on_held()
        assert events.get_nowait() == ButtonEvent(Button.B, Press.LONG)
        assert events.get_nowait() == ButtonEvent(Button.B, Press.HOLD)
        simulator._on_release(Button.B)
        assert events.empty()
        simulator._on_press(Button.B)
        simulator._on_release(Button.B)
        assert events.get_nowait() == ButtonEvent(Button.B)

    def test_long_click_repeats_while_pressed(self, simulator, tk, events):
        simulator._on_press(Button.X)
        _, on_held = tk.root.after.call_args.args
        on_held()
        for _ in range(3):
            delay, on_repeat = tk.root.after.call_args.args
            assert delay == 200
            on_repeat()
        presses = [events.get_nowait().press for _ in range(5)]
        assert presses == [Press.LONG, Press.HOLD, Press.HOLD, Press.HOLD, Press.HOLD]
        timer = tk.root.after.call_args.args
        simulator._on_release(Button.X)
        tk.root.after_cancel.assert_called_once_with(timer)
        assert events.empty()

    def test_poll_shows_the_latest_frame(self, simulator, tk):
        first = Image.new("RGB", (WIDTH, HEIGHT), (255, 0, 0))
        second = Image.new("RGB", (WIDTH, HEIGHT), (0, 255, 0))
        simulator.show(first)
        simulator.show(second)
        tk.image_tk.PhotoImage.reset_mock()
        simulator._poll()
        enlarged = tk.image_tk.PhotoImage.call_args.args[0]
        assert tk.image_tk.PhotoImage.call_count == 1
        assert enlarged.size == (WIDTH * SCALE, HEIGHT * SCALE)
        assert enlarged.getpixel((0, 0)) == (0, 255, 0)
        assert tk.root.after.call_args.args == (POLL_INTERVAL_MS, simulator._poll)

    def test_poll_without_frames(self, simulator, tk):
        tk.image_tk.PhotoImage.reset_mock()
        simulator._poll()
        tk.image_tk.PhotoImage.assert_not_called()
        assert tk.root.after.call_args.args == (POLL_INTERVAL_MS, simulator._poll)

    def test_release_without_press(self, simulator, events):
        simulator._on_release(Button.X)
        assert events.empty()

    def test_window(self, simulator, tk, on_window_closed):
        tk.root.title.assert_called_once_with(TITLE)
        assert [button.arguments["text"] for button in tk.buttons] == ["A", "B", "X", "Y"]
        cells = [
            (button.grid.call_args.kwargs["row"], button.grid.call_args.kwargs["column"])
            for button in tk.buttons
        ]
        assert cells == list(BUTTON_CELLS.values())
        assert cells == [(0, 0), (1, 0), (0, 2), (1, 2)]
        labels = [call.kwargs.get("text") for call in tk.tkinter.Label.call_args_list]
        assert labels == [None, HINT]
        tk.root.protocol.assert_called_once_with("WM_DELETE_WINDOW", on_window_closed)
        assert tk.root.after.call_args_list[0].args == (POLL_INTERVAL_MS, simulator._poll)
        tk.root.mainloop.assert_called_once_with()
        tk.root.destroy.assert_called_once_with()
        on_window_closed.assert_not_called()

    def test_window_bindings(self, simulator, tk, events):
        tk.root.bind.assert_called_once_with("<KeyPress>", simulator._on_key)
        button = tk.buttons[2]
        bindings = dict(call.args for call in button.bind.call_args_list)
        assert set(bindings) == {"<ButtonPress-1>", "<ButtonRelease-1>"}
        bindings["<ButtonPress-1>"](object())
        bindings["<ButtonRelease-1>"](object())
        assert events.get_nowait() == ButtonEvent(Button.X)

    def test_window_starts_black(self, simulator, tk):
        enlarged = tk.image_tk.PhotoImage.call_args_list[0].args[0]
        assert enlarged.size == (WIDTH * SCALE, HEIGHT * SCALE)
        assert enlarged.getextrema() == ((0, 0), (0, 0), (0, 0))
