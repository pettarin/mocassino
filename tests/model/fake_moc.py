"""A stand-in for MOC, behaving like it as far as the tests need.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

from pathlib import Path

from mocassino.model.moc import MocError, MocState, MocStatus


class FakeMoc:
    """A MOC client keeping a playlist, a current track, a position, and a state in memory.

    Like MOC, it plays a directory from its first track in name order, it starts playing
    when asked for the next track even if paused, and it ignores a jump while paused.
    """

    def __init__(
        self,
        fails_on: str | None = None,
        ignored_jumps: int = 0,
        lag: int = 0,
        repeat: bool = False,
        stuck: bool = False,
    ) -> None:
        """Initialize the stand-in.

        :param fails_on: the command that raises a MocError
        :param ignored_jumps: how many jumps are ignored, before they start working
        :param lag: for how many status requests the previous track is still reported
        :param repeat: whether the track after the last one is the first one
        :param stuck: whether asking for the next track does nothing
        """
        self.calls: list[tuple[str, object]] = []
        self.fails_on = fails_on
        self.ignored_jumps = ignored_jumps
        self.index: int | None = None
        self.lag = lag
        self.repeat = repeat
        self.seconds = 0
        self.state = MocState.STOP
        self.stuck = stuck
        self.tracks: list[str] = []
        self.volume: int | None = None
        self._stale: list[MocStatus] = []

    def _call(self, name: str, argument: object = None) -> None:
        self.calls.append((name, argument))
        if name == self.fails_on:
            raise MocError(f"{name} failed")

    def _change_track(self, index: int | None) -> None:
        self._stale = [self._status()] * self.lag
        self.index = index
        self.seconds = 0
        self.state = MocState.STOP if index is None else MocState.PLAY

    def _status(self) -> MocStatus:
        if self.index is None:
            return MocStatus()
        return MocStatus(
            current_seconds=self.seconds,
            file_path=self.tracks[self.index],
            state=self.state,
        )

    def jump(self, seconds: int) -> None:
        self._call("jump", seconds)
        if self.ignored_jumps > 0:
            self.ignored_jumps -= 1
        elif self.state is MocState.PLAY:
            self.seconds = seconds

    def load(self, path: Path) -> None:
        self._call("load", str(path))
        if path.is_dir():
            self.tracks = sorted(str(child) for child in path.iterdir())
        else:
            self.tracks = [str(path)]
        self._change_track(None)

    def names(self) -> list[str]:
        """Return the names of the commands received, in order, without the status requests."""
        return [name for name, _ in self.calls if name != "status"]

    def next(self) -> None:
        self._call("next")
        if self.stuck or self.index is None:
            return
        following = self.index + 1
        if following >= len(self.tracks):
            self._change_track(0 if self.repeat else None)
        else:
            self._change_track(following)

    def pause(self) -> None:
        self._call("pause")
        if self.state is MocState.PLAY:
            self.state = MocState.PAUSE

    def play(self, path: Path) -> None:
        self._call("play", str(path))
        if path.is_dir():
            self.tracks = sorted(str(child) for child in path.iterdir())
        else:
            self.tracks = [str(path)]
        self._change_track(0)

    def play_playlist(self) -> None:
        self._call("play_playlist")
        if self.tracks:
            self._change_track(0)

    def previous(self) -> None:
        self._call("previous")

    def seek(self, seconds: int) -> None:
        self._call("seek", seconds)

    def set_volume(self, level: int) -> None:
        self._call("set_volume", level)
        self.volume = level

    def start_server(self) -> None:
        self._call("start_server")

    def status(self) -> MocStatus:
        self._call("status")
        if self._stale:
            return self._stale.pop()
        return self._status()

    def stop(self) -> None:
        self._call("stop")
        self.index = None
        self.state = MocState.STOP

    def toggle_pause(self) -> None:
        self._call("toggle_pause")

    def unpause(self) -> None:
        self._call("unpause")
        if self.state is MocState.PAUSE:
            self.state = MocState.PLAY
