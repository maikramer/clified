"""Testes CLI output e decorators."""

from __future__ import annotations

import json
import sys
from io import StringIO

import pytest

from clified.cli.decorators import EXIT_CONFIG_ERROR, handle_cli_errors
from clified.cli.output import OutputFormatter
from clified.core.exceptions import ConfigError


def test_output_json_mode(capsys) -> None:
    out = OutputFormatter(json_mode=True)
    out.success({"tool": "x"}, message="ignored in json")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "success"
    assert data["tool"] == "x"


def test_output_quiet_suppresses_info(capsys) -> None:
    out = OutputFormatter(quiet=True)
    out.info("silencioso")
    assert capsys.readouterr().out == ""


def test_handle_cli_errors_config_exit(monkeypatch) -> None:
    @handle_cli_errors
    def boom() -> None:
        raise ConfigError("cfg inválida")

    monkeypatch.setattr(sys, "exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))

    with pytest.raises(SystemExit) as exc:
        boom()
    assert exc.value.code == EXIT_CONFIG_ERROR
