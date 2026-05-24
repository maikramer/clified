"""Testes do CLI unificado."""

from __future__ import annotations

import pytest

from clified.installer import registry as reg
from clified.installer.unified import main


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    reg.TOOLS.clear()
    reg.WORKSPACE = None
    reg._CLIFIED_ROOT = None


def test_main_list(
    sample_tools_yaml, clified_root, demo_project, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))

    code = main(["--list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "demo" in out.lower() or "Demo" in out


def test_main_list_json(
    sample_tools_yaml, clified_root, demo_project, monkeypatch, capsys
) -> None:
    import json

    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))

    code = main(["--list", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 1
    assert data["tools"][0]["name"] == "demo"


def test_main_help(sample_tools_yaml, clified_root, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    code = main([])
    assert code == 0
