"""Command line interface of mocassino.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click
import yaml

from mocassino import __version__
from mocassino.configuration import (
    BUTTONS_ORIGINS,
    DISPLAY_TARGETS,
    Configuration,
    ConfigurationError,
    load_configuration,
)


def _configuration_options(function: Callable[..., Any]) -> Callable[..., Any]:
    """Add the options selecting and overriding the configuration to a command."""
    options = [
        click.option(
            "--buttons-origin",
            type=click.Choice(BUTTONS_ORIGINS),
            help="Where the button events come from (buttons.origin).",
        ),
        click.option(
            "--configuration-file-path",
            type=click.Path(dir_okay=False, path_type=Path),
            help="YAML configuration file.",
        ),
        click.option(
            "--display-target",
            type=click.Choice(DISPLAY_TARGETS),
            help="Where the screen is drawn (display.target).",
        ),
        click.option(
            "--library-directory-path",
            type=click.Path(file_okay=False, path_type=Path),
            help="Music root directory (library.directory_path).",
        ),
        click.option(
            "--simulator",
            is_flag=True,
            help="Shortcut for '--buttons-origin simulator --display-target simulator'.",
        ),
    ]
    for option in reversed(options):
        function = option(function)
    return function


def _load_configuration(
    buttons_origin: str | None,
    configuration_file_path: Path | None,
    display_target: str | None,
    library_directory_path: Path | None,
    simulator: bool,
) -> Configuration:
    """Load the configuration, reporting the errors as command line errors."""
    if simulator:
        buttons_origin = buttons_origin or "simulator"
        display_target = display_target or "simulator"
    overrides = {
        "buttons": {"origin": buttons_origin},
        "display": {"target": display_target},
        "library": {"directory_path": library_directory_path},
    }
    try:
        return load_configuration(configuration_file_path, overrides)
    except ConfigurationError as exc:
        raise click.ClickException(str(exc)) from exc


@click.command()
@_configuration_options
def configuration(
    buttons_origin: str | None,
    configuration_file_path: Path | None,
    display_target: str | None,
    library_directory_path: Path | None,
    simulator: bool,
) -> None:
    """Print the effective configuration, in YAML format."""
    effective = _load_configuration(
        buttons_origin, configuration_file_path, display_target, library_directory_path, simulator
    )
    click.echo(yaml.safe_dump(effective.to_dict(), sort_keys=True), nl=False)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Log debug messages.")
@click.version_option(__version__, prog_name="mocassino")
def main(verbose: bool) -> None:
    """Lightweight audio player based on MOC for Pirate Audio hats."""
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )


main.add_command(configuration)
