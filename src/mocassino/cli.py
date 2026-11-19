"""Command line interface of mocassino.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import os
import shutil
import signal
import sys
from collections.abc import Callable
from logging.handlers import SysLogHandler
from pathlib import Path
from types import FrameType
from typing import Any

import click
import yaml

from mocassino import __version__
from mocassino.app import build_app
from mocassino.configuration import (
    BUTTONS_ORIGINS,
    DISPLAY_TARGETS,
    Configuration,
    ConfigurationError,
    load_configuration,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
SYSLOG_SOCKET_PATH: Path = Path("/dev/log")


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


def _daemonize() -> None:
    """Continue in a background process, detached from the terminal.

    The process in the foreground prints the identifier of the one in background and exits.
    The process in background closes all the files inherited from the one in foreground,
    so that whoever launched it is not kept waiting.
    It has no terminal to write its log messages to,
    so it sends them to the system log instead, if available.
    """
    pid = os.fork()
    if pid > 0:
        click.echo(f"mocassino is running in background (PID {pid})")
        sys.exit(0)
    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for descriptor in (0, 1, 2):
        os.dup2(null, descriptor)
    os.close(null)
    os.closerange(3, os.sysconf("SC_OPEN_MAX"))
    handlers: list[logging.Handler] = []
    if SYSLOG_SOCKET_PATH.exists():
        handler = SysLogHandler(address=str(SYSLOG_SOCKET_PATH))
        handler.setFormatter(logging.Formatter("mocassino: %(levelname)s %(name)s: %(message)s"))
        handlers.append(handler)
    logging.getLogger().handlers = handlers


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


@click.command()
@click.option(
    "--background/--foreground",
    default=True,
    help="Run detached from the terminal (default) or attached to it.",
)
@_configuration_options
def run(
    background: bool,
    buttons_origin: str | None,
    configuration_file_path: Path | None,
    display_target: str | None,
    library_directory_path: Path | None,
    simulator: bool,
) -> None:
    """Run the service."""
    effective = _load_configuration(
        buttons_origin, configuration_file_path, display_target, library_directory_path, simulator
    )
    if not effective.library.directory_path.is_dir():
        raise click.ClickException(
            f"The music root directory '{effective.library.directory_path}' does not exist"
        )
    if shutil.which(effective.system.mocp_file_path) is None:
        raise click.ClickException(f"Cannot find '{effective.system.mocp_file_path}'")
    if background:
        _daemonize()
    try:
        app = build_app(effective)

        def stop(signal_number: int, frame: FrameType | None) -> None:
            app.stop()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
        LOGGER.info("Running, press Ctrl+C or send SIGTERM to stop")
        app.run()
        LOGGER.info("Stopped")
    except Exception as exc:
        LOGGER.exception("Stopped by an error")
        raise click.ClickException(f"Stopped by an error: {exc}") from exc


main.add_command(configuration)
main.add_command(run)
