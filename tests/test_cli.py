"""Tests for the command line interface.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest
import yaml
from click.testing import CliRunner

import mocassino
from mocassino.cli import main
from mocassino.configuration import Configuration


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

    def test_configuration_file(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("playback:\n  initial_volume: 30\n", encoding="utf-8")
        result = runner.invoke(main, ["configuration", "--configuration-file-path", str(path)])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output)["playback"]["initial_volume"] == 30

    def test_configuration_file_invalid(self, runner, tmp_path):
        path = tmp_path / "custom.yaml"
        path.write_text("zoom: 2\n", encoding="utf-8")
        result = runner.invoke(main, ["configuration", "--configuration-file-path", str(path)])
        assert result.exit_code == 1
        assert "Error: Unknown configuration keys: zoom" in result.output

    def test_defaults(self, runner):
        result = runner.invoke(main, ["configuration"])
        assert result.exit_code == 0
        assert yaml.safe_load(result.output) == Configuration().to_dict()

    def test_overrides(self, runner):
        result = runner.invoke(
            main,
            [
                "configuration",
                "--buttons-origin",
                "none",
                "--display-target",
                "none",
                "--library-directory-path",
                "/srv/music",
            ],
        )
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "none"
        assert output["display"]["target"] == "none"
        assert output["library"]["directory_path"] == "/srv/music"

    def test_simulator(self, runner):
        result = runner.invoke(main, ["configuration", "--simulator"])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "simulator"
        assert output["display"]["target"] == "simulator"

    def test_simulator_does_not_override_explicit_options(self, runner):
        result = runner.invoke(main, ["configuration", "--simulator", "--display-target", "none"])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert output["buttons"]["origin"] == "simulator"
        assert output["display"]["target"] == "none"


class TestMain:
    """Tests for the main group"""

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "configuration" in result.output

    def test_verbose(self, runner):
        result = runner.invoke(main, ["--verbose", "configuration"])
        assert result.exit_code == 0

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert result.output == f"mocassino, version {mocassino.__version__}\n"
