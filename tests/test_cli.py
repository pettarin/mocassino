"""Tests for the command line interface.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import logging
import os
import signal
import threading
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

import mocassino
from mocassino.app import App
from mocassino.cli import _daemonize, _run_with_simulator, main
from mocassino.configuration import Configuration, load_configuration
from mocassino.model.moc import MocError
from mocassino.simulator.tk import TkSimulator

NULL_DESCRIPTOR = 9999


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point the home directory to a temporary one, so the user's files are never read."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def runner():
    return CliRunner()


class TestConfigurationCommand:
    """Tests for the configuration command"""

    def test_default(self, runner, home):
        directory = home / ".config" / "mocassino"
        directory.mkdir(parents=True)
        (directory / "configuration.yaml").write_text(
            "startup:\n  fixed_volume: 30\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["configuration"])
        assert yaml.safe_load(result.output)["startup"]["fixed_volume"] == 30
        result = runner.invoke(main, ["configuration", "--default"])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output) == Configuration().to_dict()

    def test_default_ignores_a_broken_configuration_file(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("zoom: 2\n", encoding="utf-8")
        result = runner.invoke(main, ["-c", str(path), "configuration", "--default"])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output) == Configuration().to_dict()

    def test_default_ignores_the_other_options(self, runner):
        arguments = ["-s", "-l", "/srv/music", "--display-target", "none", "configuration"]
        result = runner.invoke(main, [*arguments, "--default"])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output) == Configuration().to_dict()

    def test_configuration_file(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("startup:\n  fixed_volume: 30\n", encoding="utf-8")
        result = runner.invoke(main, ["--configuration-file-path", str(path), "configuration"])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output)["startup"]["fixed_volume"] == 30

    def test_configuration_file_invalid(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("zoom: 2\n", encoding="utf-8")
        result = runner.invoke(main, ["--configuration-file-path", str(path), "configuration"])
        assert result.exit_code == 1
        assert "Error: Unknown configuration keys: zoom" in result.output

    def test_defaults(self, runner):
        result = runner.invoke(main, ["configuration"])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output) == Configuration().to_dict()

    def test_output_file(self, runner, tmp_path):
        path = tmp_path / "new" / "written.yaml"
        result = runner.invoke(main, ["-s", "-l", "/srv/music", "configuration", "-o", str(path)])
        assert result.exit_code == 0
        assert result.output == f"Configuration written to '{path}'\n"
        written = load_configuration(path)
        assert written.buttons.origin == "simulator"
        assert written.display.target == "simulator"
        assert written.library.directory_path == Path("/srv/music")
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == written.to_dict()

    def test_output_file_already_exists(self, runner, tmp_path):
        path = tmp_path / "written.yaml"
        path.write_text("playback:\n  volume_step: 7\n", encoding="utf-8")
        result = runner.invoke(main, ["configuration", "--output-file-path", str(path)])
        assert result.exit_code == 1
        assert "already exists: use -y / --yes to write it anyway" in result.output
        assert path.read_text(encoding="utf-8") == "playback:\n  volume_step: 7\n"

    @pytest.mark.parametrize("option", ["-y", "--yes"])
    def test_output_file_already_exists_with_yes(self, runner, tmp_path, option):
        path = tmp_path / "written.yaml"
        path.write_text("playback:\n  volume_step: 7\n", encoding="utf-8")
        result = runner.invoke(main, ["configuration", "-o", str(path), option])
        assert result.exit_code == 0
        assert load_configuration(path) == Configuration()

    def test_output_file_cannot_be_written(self, runner, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.touch()
        path = blocker / "written.yaml"
        result = runner.invoke(main, ["configuration", "-o", str(path)])
        assert result.exit_code == 1
        assert f"Error: Cannot write '{path}'" in result.output

    def test_output_file_default_location(self, runner, home):
        path = home / ".config" / "mocassino" / "configuration.yaml"
        result = runner.invoke(main, ["--display-target", "none", "configuration", "-o"])
        assert result.exit_code == 0
        assert result.output == f"Configuration written to '{path}'\n"
        assert load_configuration(path).display.target == "none"
        result = runner.invoke(main, ["configuration", "-o"])
        assert result.exit_code == 1
        assert "already exists" in result.output
        result = runner.invoke(main, ["-s", "configuration", "-o", "-y"])
        assert result.exit_code == 0
        written = load_configuration(path)
        assert written.buttons.origin == "simulator"
        assert written.display.target == "simulator"

    def test_output_file_with_default(self, runner, home, tmp_path):
        directory = home / ".config" / "mocassino"
        directory.mkdir(parents=True)
        (directory / "configuration.yaml").write_text(
            "playback:\n  volume_step: 7\n",
            encoding="utf-8",
        )
        path = tmp_path / "defaults.yaml"
        result = runner.invoke(main, ["-s", "configuration", "--default", "-o", str(path)])
        assert result.exit_code == 0
        assert load_configuration(path) == Configuration()

    def test_overrides(self, runner):
        result = runner.invoke(
            main,
            [
                "--buttons-origin",
                "none",
                "--display-target",
                "none",
                "--library-directory-path",
                "/srv/music",
                "configuration",
            ],
        )
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "none"
        assert output["display"]["target"] == "none"
        assert output["library"]["directory_path"] == "/srv/music"

    def test_simulator(self, runner):
        result = runner.invoke(main, ["--simulator", "configuration"])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "simulator"
        assert output["display"]["target"] == "simulator"

    def test_simulator_does_not_override_explicit_options(self, runner):
        result = runner.invoke(main, ["--simulator", "--display-target", "none", "configuration"])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "simulator"
        assert output["display"]["target"] == "none"


class TestDaemonize:
    """Tests for the _daemonize function"""

    @pytest.fixture
    def root_handlers(self):
        """Restore the handlers of the root logger after the test."""
        root = logging.getLogger()
        handlers = list(root.handlers)
        yield
        root.handlers = handlers

    @pytest.fixture
    def system(self, mocker):
        """Replace the system calls, so that the tests never fork nor lose their output.

        Only the calls about the null device go to the replacements:
        the others (e.g., those of pytest itself) go to the real functions.
        """
        real_close, real_dup2, real_open = os.close, os.dup2, os.open
        system = mocker.Mock()
        system.fork = mocker.patch("mocassino.cli.os.fork", return_value=0)
        system.setsid = mocker.patch("mocassino.cli.os.setsid")
        system.closerange = mocker.patch("mocassino.cli.os.closerange")

        def fake_close(descriptor):
            if descriptor != NULL_DESCRIPTOR:
                return real_close(descriptor)
            return system.close(descriptor)

        def fake_dup2(descriptor, target, *args, **kwargs):
            if descriptor != NULL_DESCRIPTOR:
                return real_dup2(descriptor, target, *args, **kwargs)
            return system.dup2(descriptor, target)

        def fake_open(path, *args, **kwargs):
            if path != os.devnull:
                return real_open(path, *args, **kwargs)
            system.open(path, *args, **kwargs)
            return NULL_DESCRIPTOR

        mocker.patch("mocassino.cli.os.close", side_effect=fake_close)
        mocker.patch("mocassino.cli.os.dup2", side_effect=fake_dup2)
        mocker.patch("mocassino.cli.os.open", side_effect=fake_open)
        return system

    def test_background_process(self, mocker, system, root_handlers, tmp_path):
        socket_path = tmp_path / "log"
        socket_path.touch()
        mocker.patch("mocassino.cli.SYSLOG_SOCKET_PATH", socket_path)
        handler_class = mocker.patch("mocassino.cli.SysLogHandler")
        _daemonize()
        system.setsid.assert_called_once_with()
        system.open.assert_called_once_with(os.devnull, os.O_RDWR)
        descriptors = [call.args for call in system.dup2.call_args_list]
        assert descriptors == [(NULL_DESCRIPTOR, 0), (NULL_DESCRIPTOR, 1), (NULL_DESCRIPTOR, 2)]
        system.close.assert_called_once_with(NULL_DESCRIPTOR)
        system.closerange.assert_called_once_with(3, os.sysconf("SC_OPEN_MAX"))
        handler_class.assert_called_once_with(address=str(socket_path))
        assert logging.getLogger().handlers == [handler_class.return_value]

    def test_background_process_without_system_log(self, mocker, system, root_handlers, tmp_path):
        mocker.patch("mocassino.cli.SYSLOG_SOCKET_PATH", tmp_path / "missing")
        _daemonize()
        assert logging.getLogger().handlers == []

    def test_foreground_process(self, system, capsys):
        system.fork.return_value = 4242
        with pytest.raises(SystemExit) as info:
            _daemonize()
        assert info.value.code == 0
        assert capsys.readouterr().out == "mocassino is running in background (PID 4242)\n"
        system.setsid.assert_not_called()
        system.dup2.assert_not_called()
        system.closerange.assert_not_called()


class TestRunWithSimulator:
    """Tests for the _run_with_simulator function"""

    @pytest.fixture
    def app(self, mocker):
        return mocker.create_autospec(App, instance=True)

    @pytest.fixture
    def simulator(self, mocker):
        return mocker.create_autospec(TkSimulator, instance=True)

    def test_application_error(self, app, simulator):
        app.run.side_effect = MocError("Server exited!")
        with pytest.raises(MocError, match="Server exited!"):
            _run_with_simulator(app, simulator)
        simulator.close.assert_called_once_with()

    def test_both_are_run(self, app, simulator):
        threads = []
        app.run.side_effect = lambda: threads.append(threading.current_thread())
        simulator.run.side_effect = lambda **kwargs: threads.append(threading.current_thread())
        _run_with_simulator(app, simulator)
        assert len(threads) == 2
        assert threading.main_thread() in threads
        assert threads[0] is not threads[1]
        simulator.run.assert_called_once_with(on_window_closed=app.stop)
        simulator.close.assert_called_once_with()
        app.stop.assert_called_once_with()

    def test_simulator_error(self, app, simulator):
        simulator.run.side_effect = RuntimeError("no display name")
        with pytest.raises(RuntimeError, match="no display name"):
            _run_with_simulator(app, simulator)
        app.stop.assert_called_once_with()
        app.run.assert_called_once_with()


class TestMain:
    """Tests for the main group"""

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "configuration" in result.output

    def test_options_go_before_the_command(self, runner):
        result = runner.invoke(main, ["configuration", "--simulator"])
        assert result.exit_code == 2
        assert "No such option '--simulator'" in result.output

    def test_subcommand_help_does_not_load_the_configuration(self, runner):
        arguments = ["--configuration-file-path", "missing.yaml", "run", "--help"]
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        assert "--background" in result.output

    def test_short_options(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("startup:\n  fixed_volume: 30\n", encoding="utf-8")
        result = runner.invoke(main, ["-c", str(path), "-l", "/srv/music", "-s", "configuration"])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "simulator"
        assert output["display"]["target"] == "simulator"
        assert output["library"]["directory_path"] == "/srv/music"
        assert output["startup"]["fixed_volume"] == 30

    def test_verbose(self, runner):
        result = runner.invoke(main, ["--verbose", "configuration"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("option", ["-V", "--version"])
    def test_version(self, runner, option):
        result = runner.invoke(main, [option])
        assert result.exit_code == 0
        assert result.output == f"mocassino, version {mocassino.__version__}\n"


class TestRunCommand:
    """Tests for the run command"""

    @pytest.fixture
    def app(self, mocker):
        """Replace the application, so that nothing is really run."""
        app = mocker.patch("mocassino.cli.build_app").return_value
        app.simulator = None
        return app

    @pytest.fixture
    def arguments(self, tmp_path):
        """The arguments running the service on an existing directory with an existing mocp."""
        return ["--library-directory-path", str(tmp_path), "--display-target", "none", "run"]

    @pytest.fixture
    def daemonize(self, mocker):
        return mocker.patch("mocassino.cli._daemonize")

    @pytest.fixture(autouse=True)
    def set_signal(self, mocker):
        """Replace signal.signal, so that the handlers of the tests are left alone."""
        return mocker.patch("mocassino.cli.signal.signal")

    @pytest.fixture(autouse=True)
    def which(self, mocker):
        return mocker.patch("mocassino.cli.shutil.which", return_value="/usr/bin/mocp")

    @pytest.mark.parametrize("option", ["-b", "--background"])
    def test_background(self, runner, app, arguments, daemonize, option):
        result = runner.invoke(main, [*arguments, option])
        assert result.exit_code == 0
        daemonize.assert_called_once_with()
        app.run.assert_called_once_with()

    def test_background_is_the_default(self, runner, app, arguments, daemonize):
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        daemonize.assert_called_once_with()
        app.run.assert_called_once_with()

    def test_configuration_is_used(self, runner, mocker, arguments, daemonize, tmp_path):
        build_app = mocker.patch("mocassino.cli.build_app")
        build_app.return_value.simulator = None
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        effective, configuration_file_path = build_app.call_args.args
        assert configuration_file_path is None
        assert effective.display.target == "none"
        assert effective.library.directory_path == tmp_path

    def test_configuration_file_is_passed_on(self, runner, mocker, arguments, daemonize, tmp_path):
        build_app = mocker.patch("mocassino.cli.build_app")
        build_app.return_value.simulator = None
        path = tmp_path / "custom.yaml"
        path.write_text("startup:\n  fixed_volume: 30\n", encoding="utf-8")
        result = runner.invoke(main, ["-c", str(path), *arguments])
        assert result.exit_code == 0
        effective, configuration_file_path = build_app.call_args.args
        assert effective.startup.fixed_volume == 30
        assert configuration_file_path == path

    def test_error_while_building(self, runner, mocker, arguments, daemonize):
        mocker.patch("mocassino.cli.build_app", side_effect=OSError("cannot open resource"))
        result = runner.invoke(main, arguments)
        assert result.exit_code == 1
        assert "Error: Stopped by an error: cannot open resource" in result.output

    def test_error_while_running(self, runner, app, arguments, daemonize):
        app.run.side_effect = MocError("Server exited!")
        result = runner.invoke(main, arguments)
        assert result.exit_code == 1
        assert "Error: Stopped by an error: Server exited!" in result.output

    @pytest.mark.parametrize("option", ["-f", "--foreground"])
    def test_foreground(self, runner, app, arguments, daemonize, option):
        result = runner.invoke(main, [*arguments, option])
        assert result.exit_code == 0
        daemonize.assert_not_called()
        app.run.assert_called_once_with()

    def test_invalid_configuration(self, runner, app, arguments, daemonize):
        result = runner.invoke(main, ["--configuration-file-path", "missing.yaml", *arguments])
        assert result.exit_code == 1
        assert "Error: Cannot read configuration file" in result.output
        daemonize.assert_not_called()

    def test_mocp_not_found(self, runner, app, arguments, daemonize, which):
        which.return_value = None
        result = runner.invoke(main, arguments)
        assert result.exit_code == 1
        assert "Error: Cannot find 'mocp'" in result.output
        daemonize.assert_not_called()
        app.run.assert_not_called()

    def test_music_root_directory_missing(self, runner, app, daemonize, tmp_path):
        missing = tmp_path / "missing"
        result = runner.invoke(main, ["--library-directory-path", str(missing), "run"])
        assert result.exit_code == 1
        assert f"Error: The music root directory '{missing}' does not exist" in result.output
        daemonize.assert_not_called()
        app.run.assert_not_called()

    def test_simulator(self, runner, mocker, app, arguments, daemonize):
        run_with_simulator = mocker.patch("mocassino.cli._run_with_simulator")
        app.simulator = mocker.sentinel.simulator
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        run_with_simulator.assert_called_once_with(app, mocker.sentinel.simulator)
        app.run.assert_not_called()

    @pytest.mark.parametrize(
        ("mode", "options", "detached"),
        [
            ("background", [], True),
            ("foreground", [], False),
            ("background", ["-f"], False),
            ("background", ["--foreground"], False),
            ("foreground", ["-b"], True),
            ("foreground", ["--background"], True),
            ("foreground", ["-f"], False),
            ("background", ["-b"], True),
        ],
    )
    @pytest.mark.parametrize("simulator", [[], ["-s"]])
    def test_run_mode(self, runner, app, daemonize, tmp_path, mode, options, detached, simulator):
        path = tmp_path / "custom.yaml"
        path.write_text(f"run:\n  mode: {mode}\n", encoding="utf-8")
        arguments = ["-c", str(path), "-l", str(tmp_path), *simulator, "run", *options]
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        assert daemonize.call_count == (1 if detached else 0)

    def test_signals_stop_the_application(self, runner, app, arguments, daemonize, set_signal):
        result = runner.invoke(main, arguments)
        assert result.exit_code == 0
        handlers = {call.args[0]: call.args[1] for call in set_signal.call_args_list}
        assert set(handlers) == {signal.SIGINT, signal.SIGTERM}
        app.stop.assert_not_called()
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        app.stop.assert_called_once_with()
