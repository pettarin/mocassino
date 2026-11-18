# mocassino

Lightweight audio player based on MOC
for Raspberry Pi Zero 2 devices with Pimoroni Pirate Audio hats


## Overview

TBW


## Features

TBW


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

You should be able to run ... TBW

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

You should be able to run ... TBW


## Usage

### Service Usage

TBW

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
TBW
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

