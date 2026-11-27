# Development

> [!NOTE]
> The examples in the documentation use `micromamba`
> to manage virtual environments; feel free to replace it
> with your favorite tool (`conda`, `uv`, etc.).

## Setup Development Environment

Clone this repository and install from source
in a virtual environment, with development extras:

```bash
$ git clone https://github.com/pettarin/mocassino
$ cd mocassino

$ micromamba create -n mocassino_dev python=3.13
$ micromamba activate mocassino_dev

(mocassino_dev) $ pip install -e ".[dev]"
(mocassino_dev) $ # or
(mocassino_dev) $ make install-e-this-dev
```

> [!NOTE]
> The `dev` option installs all the extras
> of the regular PyPI package `mocassino`,
> plus additional tools (e.g., `coverage`, `mypy`, `ruff`, etc.)
> needed for development activities.

You should be able to run the `mocassino` CLI tool,
automatically installed in the virtual environment:

```bash
(mocassino_dev) $ mocassino version
mocassino, version 0.0.6
```

To run the service (in foreground) on a device
with the actual Pimoroni Pirate Audio hat:

```bash
(mocassino_dev) $ mocassino run --foreground
```

When developing (on a PC) it is possible to leverage
the Tk-based simulator, starting it with:

```bash
(mocassino_dev) $ mocassino --simulator run --foreground
```

The
[CLI Usage](cli/INDEX.md)
guide describes all the commands, subcommands, and most of the options
of the CLI tool `mocassino`.


## Running Tests

```bash
# Run all checks (unit tests, linter, and type checker)
(mocassino_dev) $ make test-all
# OR equivalently
(mocassino_dev) $ make test

# Run unit tests only
(mocassino_dev) $ make test-unit

# Run unit tests with coverage (HTML report produced in the `htmlcov/` directory)
(mocassino_dev) $ make coverage

# Run linter
(mocassino_dev) $ make lint

# Run type checker
(mocassino_dev) $ make check-type-hints
```

## Usage

### Service Usage

Run the service with the `mocassino run` command.
By default it runs in background, detached from the terminal:

```bash
$ mocassino run
mocassino is running in background (PID 15875)
```

To stop the service, send it the `SIGTERM` signal (e.g., `kill 15875`).

For development, it is normally helpful to run it on foreground:

```bash
$ mocassino run --foreground
```

To stop the service, send a `CTRL+C` in the shell running it,
or a `SIGTERM` signal from another shell.

To try the service on a PC without the hardware,
specify the global option `--simulator`,
which shows a Tk-based window that emulates
the hat display and buttons:

```bash
$ mocassino --simulator run --foreground
```

### CLI Usage

The
[CLI Usage](cli/INDEX.md)
guide describes all the commands, subcommands, and most of the options
of the CLI tool `mocassino`.


## Project Structure

TODO: run tree and annotate its output

## Branching And Versioning Policy

### Branch `main`

- Branch `main` is protected, and it represents the sources of the latest stable release.
- Only the maintainer is allowed to push there directly,
  usually merging the `devel` branch when preparing a new release.
- Published packages on PyPI are from commit tagged `vX.Y.Z`.

### Branch `devel`

- Branch `devel` is protected, and it accumulates fixes and features for the next release.
- The maintainer is allowed to push there directly,
  usually merging feature or fix branches.
- Other contributors should open pull requests
  (see the [CONTRIBUTING](CONTRIBUTING.md) document)
  against the `devel` branch, which will be reviewed and, if appropriate, merged.

### Other Branches

- Fix branches should be named `fix/gh_#123_short_description`
  where `#123` is the ID of the GitHub issue being fixed.
- Feature branches should be named `feature/gh_#456_short_description`
  where `#456` is the ID of the GitHub issue describing the requested feature.
- In both cases, it is mandatory to have a GitHub issue
  describing the issue being fixed or the new feature being added.
- No need to squash commits on a fix or feature branch,
  just try to have meaningful commit messages if you have more than one commit.
  Usually it is preferable referencing the GitHub issue
  (`Fixes #123 ...` or `Implement #456 ...`) in the commit message.

### Versioning

- This project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).
- Each released version is published on PyPI as package
[mocassino](https://pypi.org/project/mocassino/)
and the corresponding commit tagged with `vX.Y.Z`,
where `mocassino==X.Y.Z` is the released version.


## Contributing

See the
[CONTRIBUTING](CONTRIBUTING.md)
document.

