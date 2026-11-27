# mocassino

Lightweight audio player based on MOC
for Raspberry Pi Zero 2 devices with Pimoroni Pirate Audio hats


## Overview

`mocassino` is a background service
turning a Raspberry Pi device with a Pimoroni Pirate Audio hat
into a small standalone audio player.

The service handles the four buttons of the hat,
pilots its display, and delegates the playback to
[MOC](https://moc.daper.net/) (music on console),
which it controls by running `mocp` commands.


## Features

- Playback control with the buttons of the hat:
  play/pause, previous/next track,
  seek backward/forward, volume down/up
- Playback information on the display of the hat:
  artist, title, and album of the current track,
  playback progress, volume, and the icons of the actions of the buttons
- Menu to browse the music root directory
  and play a directory or a single FLAC, MP3, OGG, or WAV file
- Menu to change most of the settings of the running service
- Settings stored in a YAML configuration file
- Simulator window replacing the buttons and the display,
  to run the service on a PC without the hardware


## Requirements

- A Raspberry Pi device with a Pimoroni Pirate Audio hat,
  with MOC (music on console) installed
- Python 3.13 or later
- A package/virtual environment manager tool (e.g., `micromamba`, `conda`, `uv`, etc.)


## Installation

### Using The Installer Script (Recommended)

First, download the install script:

```bash
cd /tmp
curl -kO https://raw.githubusercontent.com/pettarin/mocassino/refs/heads/main/install.sh
```

Inspect all the available options with `--help`:

```bash
bash install.sh --help
```

Then install the service, adding the relevant options as needed.
This requires privilege elevation, for instace with `sudo`:

```bash
# install the service with the default options
sudo bash install.sh

# install the service, with some custom options set
# useful on a Raspberry Pi Zero 2 with DietPi OS
sudo bash install.sh --display-orientation 180 --library-directory-path /music --run-as-group audio --run-as-user dietpi
```

The installation script starts the service,
you should be seeing its interface drawn
on the display of the hat.

To uninstall the service and remove all files created by it:

```bash
sudo bash install.sh --uninstall
```

### Developers And Advanced Users

`mocassino` is published on PyPI as the same-name package
[mocassino](https://pypi.org/project/mocassino/).

Developers and advanced users might want to setup a development environment
instead of relying on the installation script described above. See the
[DEVELOPMENT](https://github.com/pettarin/mocassino/blob/main/docs/DEVELOPMENT.md)
documentation for the details.


## Usage

The installation script installs `mocassino`
to be run in background via a `systemd` service,
which is started automatically when the device boots up
and after the installation.

The MOC server is started automatically, if it is not already running.

By default, `mocassino` restores both the playback and volume state
that were saved the last time the service ran.
It is possible to change this behavior in the Settings menu
(see below).

### Buttons

TODO add a picture of the board here

| Button | Location     |
|--------|--------------|
| `A`    | Top Left     |
| `B`    | Bottom Left  |
| `X`    | Top Right    |
| `Y`    | Bottom Right |

### Playback Mode

TODO add screenshots here

The default actions for the four buttons of the hat are:

| Button | Short Click  | Long/Hold Click |
|--------|--------------------------------|
| `A`    | Play/pause   | Open the menu   |
| `B`    | Next track   | Previous track  |
| `X`    | Volume up    | Seek forward    |
| `Y`    | Volume down  | Seek backward   |

### Menu Mode

TODO add screenshots here

The default actions for the four buttons of the hat are:

| Button | Short Click    | Long/Hold Click |
|--------|----------------|-----------------|
| `A`    | Back one level | (None)          |
| `B`    | Select         | (None)          |
| `X`    | Up             | Select          |
| `Y`    | Down           | Select          |

### Configuration Files

The permanent settings, including the action of each button,
are stored in the `~/.config/mocassino/configuration.yaml` file,
an example of which is located at
[res/configuration/configuration.yaml](https://github.com/pettarin/mocassino/blob/main/res/configuration/configuration.yaml).
Most of the settings can be changed directly through the service menus,
thus not requiring a local or SSH connection to the device running `mocassino`.

The state of the player is stored in the
`~/.config/mocassino/state.yaml` file,
an example of which is located at
[res/configuration/state.yaml](https://github.com/pettarin/mocassino/blob/main/res/configuration/state.yaml).
Regular users do not need to alter this file.

### CLI Usage

The
[CLI Usage](https://github.com/pettarin/mocassino/blob/main/docs/cli/INDEX.md)
guide describes all the commands, subcommands, and most of the options
of the CLI tool `mocassino`.


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

The bundled Roboto Regular font is licensed under
the SIL Open Font License 1.1, see the
[OFL.txt](https://github.com/pettarin/mocassino/blob/main/src/mocassino/res/font/OFL.txt)
file for details.


## Authors

- Alberto Pettarin ([Web](https://www.albertopettarin.it))

