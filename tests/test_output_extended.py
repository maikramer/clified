"""Testes adicionais OutputFormatter."""

from __future__ import annotations

import json

import pytest

from clified.cli.output import OutputFormatter, get_output_formatter


def test_output_error_json(capsys: pytest.CaptureFixture[str]) -> None:
    out = OutputFormatter(json_mode=True)
    out.error("falhou", details={"code": 1})
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "error"
    assert data["error"] == "falhou"
    assert data["details"]["code"] == 1


def test_output_table_json(capsys: pytest.CaptureFixture[str]) -> None:
    out = OutputFormatter(json_mode=True)
    rows = [{"name": "a", "kind": "python"}]
    out.table(rows, columns=["name", "kind"], title="Tools")
    data = json.loads(capsys.readouterr().out)
    assert data["items"] == rows
    assert data["count"] == 1


def test_output_warn_alias() -> None:
    out = OutputFormatter(quiet=True)
    out.warn("x")  # não deve levantar


def test_get_output_formatter_default() -> None:
    fmt = get_output_formatter(None)
    assert isinstance(fmt, OutputFormatter)
    assert fmt.is_json is False
