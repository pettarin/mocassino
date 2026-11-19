"""Command line interface of mocassino.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import os
import shutil
import signal
import sys
import threading
from dataclasses import dataclass
from logging.handlers import SysLogHandler
from pathlib import Path
from types import FrameType

import click
import yaml

from mocassino import __version__
from mocassino.app import App, build_app
from mocassino.configuration import (
    BUTTONS_ORIGINS,
    DISPLAY_TARGETS,
    Configuration,
    ConfigurationError,
    load_configuration,
)
from mocassino.simulator.tk import TkSimulator

LOGGER: logging.Logger = logging.getLogger(__name__)
SYSLOG_SOCKET_PATH: Path = Path("/dev/log")


@dataclass(frozen=True)
class GlobalOptions:
    """The options given before the command, shared by all the commands.

    They select and override the configuration.
    """

    buttons_origin: str | None
    configuration_file_path: Path | None
    display_target: str | None
    library_directory_path: Path | None
    simulator: bool


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


def _load_configuration(options: GlobalOptions) -> Configuration:
    """Load the configuration, reporting the errors as command line errors."""
    buttons_origin, display_target = options.buttons_origin, options.display_target
    if options.simulator:
        buttons_origin = buttons_origin or "simulator"
        display_target = display_target or "simulator"
    overrides = {
        "buttons": {"origin": buttons_origin},
        "display": {"target": display_target},
        "library": {"directory_path": options.library_directory_path},
    }
    try:
        return load_configuration(options.configuration_file_path, overrides)
    except ConfigurationError as exc:
        raise click.ClickException(str(exc)) from exc


def _run_with_simulator(app: App, simulator: TkSimulator) -> None:
    """Run the application in another thread, and the simulator in this (the main) one.

    Either of them ending makes the other end too.

    :raises Exception: the error that stopped the application, if any
    """
    errors: list[Exception] = []

    def run_app() -> None:
        try:
            app.run()
        except Exception as exc:
            errors.append(exc)
        finally:
            simulator.close()

    thread = threading.Thread(target=run_app, name="mocassino-app")
    thread.start()
    try:
        simulator.run(on_window_closed=app.stop)
    finally:
        app.stop()
        thread.join()
    if errors:
        raise errors[0]


@click.command()
@click.option(
    "--default",
    is_flag=True,
    help="Print the default values, ignoring the configuration file and the other options.",
)
@click.pass_obj
def configuration(options: GlobalOptions, default: bool) -> None:
    """Print the effective configuration, in YAML format."""
    effective = Configuration() if default else _load_configuration(options)
    click.echo(yaml.safe_dump(effective.to_dict(), sort_keys=True), nl=False)


@click.group()
@click.option(
    "--buttons-origin",
    type=click.Choice(BUTTONS_ORIGINS),
    help="Where the button events come from (buttons.origin).",
)
@click.option(
    "-c",
    "--configuration-file-path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="YAML configuration file.",
)
@click.option(
    "--display-target",
    type=click.Choice(DISPLAY_TARGETS),
    help="Where the screen is drawn (display.target).",
)
@click.option(
    "-l",
    "--library-directory-path",
    type=click.Path(file_okay=False, path_type=Path),
    help="Music root directory (library.directory_path).",
)
@click.option(
    "-s",
    "--simulator",
    is_flag=True,
    help="Shortcut for '--buttons-origin simulator --display-target simulator'.",
)
@click.option("-v", "--verbose", is_flag=True, help="Log debug messages.")
@click.version_option(__version__, "-V", "--version", prog_name="mocassino")
@click.pass_context
def main(
    context: click.Context,
    buttons_origin: str | None,
    configuration_file_path: Path | None,
    display_target: str | None,
    library_directory_path: Path | None,
    simulator: bool,
    verbose: bool,
) -> None:
    """Lightweight audio player based on MOC for Pirate Audio hats.

    The options go before the command, and are shared by all the commands.
    """
    context.obj = GlobalOptions(
        buttons_origin=buttons_origin,
        configuration_file_path=configuration_file_path,
        display_target=display_target,
        library_directory_path=library_directory_path,
        simulator=simulator,
    )
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )


@click.command()
@click.option(
    "-b/-f",
    "--background/--foreground",
    default=True,
    help="Run detached from the terminal (default) or attached to it.",
)
@click.pass_obj
def run(options: GlobalOptions, background: bool) -> None:
    """Run the service."""
    effective = _load_configuration(options)
    if not effective.library.directory_path.is_dir():
        raise click.ClickException(
            f"The music root directory '{effective.library.directory_path}' does not exist"
        )
    if shutil.which(effective.system.mocp_file_path) is None:
        raise click.ClickException(f"Cannot find '{effective.system.mocp_file_path}'")
    if background:
        _daemonize()
    try:
        app = build_app(effective, options.configuration_file_path)

        def stop(signal_number: int, frame: FrameType | None) -> None:
            app.stop()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
        LOGGER.info("Running, press Ctrl+C or send SIGTERM to stop")
        if app.simulator is None:
            app.run()
        else:
            _run_with_simulator(app, app.simulator)
        LOGGER.info("Stopped")
    except Exception as exc:
        LOGGER.exception("Stopped by an error")
        raise click.ClickException(f"Stopped by an error: {exc}") from exc


main.add_command(configuration)
main.add_command(run)
