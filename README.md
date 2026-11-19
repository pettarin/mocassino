# mocassino

Lightweight audio player based on MOC
for Raspberry Pi Zero 2 devices with Pimoroni Pirate Audio hats


## Overview

`mocassino` is a background service
turning a Raspberry Pi Zero 2 with a Pimoroni Pirate Audio hat
into a small standalone audio player.

The service handles the four buttons of the hat,
pilots its display, and delegates the playback to
[MOC](https://moc.daper.net/) (music on console),
which it controls by running `mocp` commands.


## Features

- Playback control with the buttons of the hat:
  play/pause, next track, previous track, seek backward and forward,
  volume up, volume down
- Playback information on the display of the hat:
  artist, title, and album of the current track,
  playback progress, volume, and the icons of the actions of the buttons
- Menu to browse the music root directory
  and play a directory or a single FLAC, MP3, OGG, or WAV file
- Menu showing the name and the IP address of the host,
  and shutting it down
- Menu to change the settings of the running service
- Settings stored in a YAML configuration file,
  including the action of each button
- Simulator window replacing the buttons and the display,
  to run the service on a PC without the hardware


## Requirements

- Python 3.13 or later
- A package/virtual environment manager tool (e.g., `micromamba`, `conda`, `uv`, etc.)
- A Raspberry Pi Zero 2 with a Pimoroni Pirate Audio hat,
  with MOC (music on console) installed


## Installation

> [!NOTE]
> The examples in the documentation use `micromamba`
> to manage virtual environments; feel free to replace it
> with your favorite tool (`conda`, `uv`, etc.).

### From PyPI (Recommended)

`mocassino` is published on PyPI as the same-name package
[mocassino](https://pypi.org/project/mocassino/)
, and this is the recommended way of installing it for most users.

Only the first time: create a virtual environment,
activate it, and install the latest release of `mocassino`
available on PyPI with `pip`:

```bash
$ micromamba create -n mocassino_env python=3.13
$ micromamba activate mocassino_env

(mocassino_env) $ pip install mocassino
```

You should be able to run the CLI tool `mocassino`:

```bash
(mocassino_env) $ mocassino --version
```

To update `mocassino`, use the `-U / --upgrade` option:

```bash
$ micromamba activate mocassino_env

(mocassino_env) $ pip install mocassino --upgrade
```


### From Source

Clone this repository and install from source
in a virtual environment:

```bash
$ git clone https://github.com/pettarin/mocassino
$ cd mocassino

$ micromamba create -n mocassino_env python=3.13
$ micromamba activate mocassino_env

(mocassino_env) $ pip install -e .
(mocassino_env) $ # or
(mocassino_env) $ make install-e-this
```

You should be able to run the CLI tool `mocassino`:

```bash
(mocassino_env) $ mocassino --version
```


## Usage

### Service Usage

Run the service with the `mocassino run` command.
By default it runs in background, detached from the terminal:

```bash
$ mocassino --library-directory-path /home/pi/music run
mocassino is running in background (PID 15875)
```

The MOC server is started automatically, if it is not already running.

> [!NOTE]
> When it starts, the service sets the MOC volume to the one it saved
> when it last ran or, the first time, to the `playback.volume_default` setting (50 by default).

The buttons of the hat are
`A` (top-left), `B` (bottom-left), `X` (top-right), and `Y` (bottom-right).
By default they perform the following actions:

| Button | Playback mode | Menu mode |
|---|---|---|
| `A` | Play/pause; hold: open the menu | Back, up one level |
| `B` | Next track; hold: previous track | Select |
| `X` | Volume up; hold: seek forward | Up; hold: select |
| `Y` | Volume down; hold: seek backward | Down; hold: select |

The permanent settings, including the action of each button,
can be stored in the `~/.config/mocassino/configuration.yaml` file:

```yaml
display:
  font_file_path: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
library:
  directory_path: /home/pi/music
```

To stop the service, send it the `SIGTERM` signal (e.g., `kill 15875`).

> [!NOTE]
> Installing the service as a systemd unit is not available yet.

To try the service on a PC without the hardware,
run it in foreground with the simulator window:

```bash
$ mocassino --simulator --library-directory-path ~/music run --foreground
```

### CLI Usage

The
[CLI Usage](https://github.com/pettarin/mocassino/blob/main/docs/cli/INDEX.md)
guide describes all the commands, subcommands, and most of the options
of the CLI tool `mocassino`.

Some examples of the commands made available
by the CLI tool `mocassino` in the virtual enviroment
where it is installed:

> [!NOTE]
> For the sake of brevity, in the following examples:
> - the `(mocassino_env) $` shell prompt is omitted;
> - some commands are shown without their output or with truncated output;
> - several commands and options are not illustrated.
> Consult the
> [CLI Usage](https://github.com/pettarin/mocassino/blob/main/docs/cli/INDEX.md)
> for a comprehensive guide of the CLI tool `mocassino`.

```bash
$ # print the version
$ mocassino --version

$ # run the service in background (default)
$ mocassino run

$ # run the service in foreground, logging debug messages
$ mocassino --verbose run --foreground

$ # run the service with a given configuration file
$ mocassino --configuration-file-path /path/to/configuration.yaml run

$ # run the service on a PC, with the simulator window
$ mocassino --simulator --library-directory-path ~/music run --foreground

$ # run the service with the buttons of the hat, but without drawing on its display
$ mocassino --display-target none run

$ # print the effective configuration
$ mocassino configuration
```


## Releases And Changelog

The list of releases and their changes is contained
in the
[CHANGELOG](https://github.com/pettarin/mocassino/blob/main/docs/CHANGELOG.md)
document.


## Development

Consult the
[DEVELOPMENT](https://github.com/pettarin/mocassino/blob/main/docs/DEVELOPMENT.md)
document to learn how to set up a development environment,
run the tests, and browse the project structure.

The
[CONTRIBUTING](https://github.com/pettarin/mocassino/blob/main/docs/CONTRIBUTING.md)
document explains how to report issues and propose changes.


## License

This project is licensed under
the GNU General Public License v3.0 or later (GPLv3+).

See the
[LICENSE](https://github.com/pettarin/mocassino/blob/main/LICENSE)
file for details.


## Authors

- Alberto Pettarin ([Web](https://www.albertopettarin.it))

