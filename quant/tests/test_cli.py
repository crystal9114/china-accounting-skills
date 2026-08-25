from __future__ import annotations

from typer.testing import CliRunner

from qsys.cli import app


runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "qsys" in result.stdout


def test_demo(cfg_path):
    result = runner.invoke(app, ["demo", "--config", str(cfg_path)])
    assert result.exit_code == 0, result.stdout + str(result.exception)
    assert "ingested" in result.stdout
    assert "paper equity" in result.stdout
